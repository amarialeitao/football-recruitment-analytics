"""Player Profile: what a player brings, compared with peers, and how sure we can be."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scouting.insights import player_insights
from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.metrics.percentiles import PCT_SUFFIX
from scouting.ui import charts
from scouting.ui import components as c
from scouting.ui.ai_note import ai_note_block
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label, t
from scouting.ui.players import (
    confidence_for_minutes,
    go_to,
    money,
    player_selector,
    season_label,
    tr,
)

TEXT = {
    "title": {"en": "Player Profile", "pt": "Perfil do jogador"},
    "question": {
        "en": "What does this player bring, and how sure can we be?",
        "pt": "O que este jogador acrescenta, e com que segurança o podemos dizer?",
    },
    "choose": {"en": "Player", "pt": "Jogador"},
    "age": {"en": "Age", "pt": "Idade"},
    "position": {"en": "Position", "pt": "Posição"},
    "club": {"en": "Club", "pt": "Clube"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "value": {"en": "Market value (end of season)", "pt": "Valor de mercado (fim da época)"},
    "contract": {"en": "Contract until", "pt": "Contrato até"},
    "profile_title": {
        "en": "Percentile profile vs {n} {pos} in the same season",
        "pt": "Perfil em percentis vs {n} {pos} na mesma época",
    },
    "profile_how": {
        "en": "Each bar is the player's percentile among players of the same position group "
        "with at least {min} minutes in the season, across all leagues in scope. 100 is the best "
        "value in the group (for metrics where lower is better, such as goals conceded or cards, "
        "the scale is inverted). The dotted line marks the median. Hover a bar for the raw value.",
        "pt": "Cada barra é o percentil do jogador entre jogadores do mesmo grupo de posição com "
        "pelo menos {min} minutos na época, em todas as ligas analisadas. 100 é o melhor valor "
        "do grupo (em métricas onde menor é melhor, como golos sofridos ou cartões, a escala é "
        "invertida). A linha pontilhada marca a mediana. Passe o rato para ver o valor bruto.",
    },
    "value_title": {
        "en": "Market value: {start} at the start of the season, {end} at the end",
        "pt": "Valor de mercado: {start} no início da época, {end} no fim",
    },
    "value_how": {
        "en": "Transfermarkt market value estimates over time; the shaded band is the selected "
        "season. A market value is a crowd estimate, not a transfer fee.",
        "pt": "Estimativas de valor de mercado do Transfermarkt ao longo do tempo; a faixa "
        "sombreada é a época selecionada. Valor de mercado é uma estimativa, não um preço de "
        "transferência.",
    },
    "minutes_title": {
        "en": "Availability: minutes per season (label = share of team minutes)",
        "pt": "Disponibilidade: minutos por época (rótulo = % dos minutos da equipa)",
    },
    "minutes_how": {
        "en": "League minutes in each season and league in scope. Bars in blue reach the minimum "
        "for comparisons; grey bars do not.",
        "pt": "Minutos de liga em cada época e liga analisadas. Barras azuis atingem o mínimo "
        "para comparações; as cinzentas não.",
    },
    "similar": {"en": "Find similar players", "pt": "Procurar jogadores parecidos"},
    "metric": {"en": "Metric", "pt": "Métrica"},
    "raw": {"en": "Value", "pt": "Valor"},
    "pct": {"en": "Percentile", "pt": "Percentil"},
    "no_history": {
        "en": "No market value history for this player.",
        "pt": "Sem histórico de valor de mercado para este jogador.",
    },
}

settings, data = setup_page("Player Profile")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))

candidates = universe[universe["competition_id"].isin(filters.competitions)]
row = player_selector(
    candidates,
    lang,
    label=tr(TEXT["choose"], lang),
    prefer_competition=settings.scope.focus_competition,
)
if row is None:
    st.stop()

min_minutes = settings.analysis.min_minutes
thresholds = (
    settings.analysis.confidence_minutes.medium,
    settings.analysis.confidence_minutes.high,
)
confidence = confidence_for_minutes(row["minutes"], thresholds)
contract = row["contract_expiration_date"]

c.kpi_row(
    [
        c.Kpi(num(row["age"], lang, 1), tr(TEXT["age"], lang)),
        c.Kpi(position_label(row["sub_position"], lang), tr(TEXT["position"], lang)),
        c.Kpi(str(row["club_name"]), tr(TEXT["club"], lang), str(row["competition_name"])),
        c.Kpi(
            num(row["minutes"], lang),
            tr(TEXT["minutes"], lang),
            t(f"confidence_{confidence}", lang),
        ),
        c.Kpi(
            money(row["market_value_end"], lang),
            tr(TEXT["value"], lang),
            f"{tr(TEXT['contract'], lang)} "
            + ("—" if pd.isna(contract) else contract.date().isoformat()),
        ),
    ]
)

insights = player_insights(
    row,
    confidence_minutes=thresholds,
    min_minutes=min_minutes,
    sample_thresholds=(
        settings.analysis.confidence_sample.medium,
        settings.analysis.confidence_sample.high,
    ),
)
group = row["position_group"]
footer = c.source_note(
    lang,
    data_cutoff=data.data_cutoff,
    season_label=season_label(int(row["season"])),
    population=f"n={num(row['comparison_n'], lang)}" if pd.notna(row["comparison_n"]) else None,
)

if row["minutes"] >= min_minutes and group in PROFILE_METRICS:
    keys = list(PROFILE_METRICS[group])
    strengths = [i for i in insights if i.key.startswith("strength:")]
    title = (
        strengths[0].title(lang)
        if strengths
        else tr(TEXT["profile_title"], lang).format(
            n=num(row["comparison_n"], lang), pos=t(group, lang).lower()
        )
    )
    observed = pd.DataFrame(
        {
            tr(TEXT["metric"], lang): [metric(k).label_for(lang) for k in keys],
            tr(TEXT["raw"], lang): [
                "—" if pd.isna(row[k]) else metric(k).fmt.format(float(row[k])) for k in keys
            ],
            tr(TEXT["pct"], lang): [row[k + PCT_SUFFIX] for k in keys],
        }
    )
    c.chart_block(
        charts.percentile_profile(row, keys, lang, title=title),
        lang=lang,
        footer=footer,
        how_to_read=tr(TEXT["profile_how"], lang).format(min=num(min_minutes, lang)),
        insights=insights,
        observed=observed,
        key="profile",
    )
else:
    c.insight_list(insights, lang)

history = data.valuations[data.valuations["player_id"] == row["player_id"]]
if history.empty:
    st.info(tr(TEXT["no_history"], lang))
else:
    c.chart_block(
        charts.value_trajectory(
            history,
            lang,
            title=tr(TEXT["value_title"], lang).format(
                start=money(row["market_value_start"], lang),
                end=money(row["market_value_end"], lang),
            ),
            season=int(row["season"]),
        ),
        lang=lang,
        footer=c.source_note(lang, data_cutoff=data.data_cutoff),
        how_to_read=tr(TEXT["value_how"], lang),
        key="value",
    )

career = data.players[data.players["player_id"] == row["player_id"]]
c.chart_block(
    charts.minutes_by_season(career, lang, title=tr(TEXT["minutes_title"], lang)),
    lang=lang,
    footer=c.source_note(lang, data_cutoff=data.data_cutoff),
    how_to_read=tr(TEXT["minutes_how"], lang),
    key="minutes",
)

strength = data.league_strength[
    (data.league_strength["competition_id"] == row["competition_id"])
    & (data.league_strength["season"] == row["season"])
]["strength_index"]
ai_note_block(
    row,
    settings=settings,
    lang=lang,
    confidence=confidence,
    insights=insights,
    league_strength_index=None if strength.empty else float(strength.iloc[0]),
)

c.unavailable_metrics(lang)
if st.button(tr(TEXT["similar"], lang), type="primary"):
    go_to("similar", row)
