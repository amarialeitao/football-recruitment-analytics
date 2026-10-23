"""Player Profile: what a player brings, compared with peers, and how sure we can be."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scouting.insights import POSITION_LABEL, player_insights
from scouting.metrics import trend
from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.metrics.percentiles import PCT_SUFFIX
from scouting.report import ReportInput, player_report_html, report_filename
from scouting.ui import charts
from scouting.ui import components as c
from scouting.ui import shortlist as sl
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
    "age": {"en": "years old", "pt": "anos"},
    "age_note": {
        "en": "on 1 January {year}, mid-season",
        "pt": "a 1 de janeiro de {year}, a meio da época",
    },
    "position": {"en": "main position", "pt": "posição principal"},
    "position_note": {
        "en": "his percentiles compare him with {group}",
        "pt": "os percentis comparam-no com {group}",
    },
    "club": {"en": "club where he played most", "pt": "clube onde mais jogou"},
    "minutes": {"en": "league minutes this season", "pt": "minutos de liga nesta época"},
    "minutes_note": {
        "en": "{share:.0%} of his team's minutes · {conf}",
        "pt": "{share:.0%} dos minutos da equipa · {conf}",
    },
    "value": {
        "en": "market value at the end of the season",
        "pt": "valor de mercado no fim da época",
    },
    "contract": {
        "en": "Transfermarkt estimate · contract until",
        "pt": "estimativa Transfermarkt · contrato até",
    },
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
        "en": "League minutes in each season and league in scope. Black bars reach the minimum "
        "for comparisons; grey bars do not.",
        "pt": "Minutos de liga em cada época e liga analisadas. Barras azuis atingem o mínimo "
        "para comparações; as cinzentas não.",
    },
    "trend_heading": {"en": "Change since last season", "pt": "Evolução face à época anterior"},
    "trend_title_up": {
        "en": "Biggest change since {before}: {metric} improved (percentile {a} → {b})",
        "pt": "Maior mudança desde {before}: {metric} melhorou (percentil {a} → {b})",
    },
    "trend_title_down": {
        "en": "Biggest change since {before}: {metric} declined (percentile {a} → {b})",
        "pt": "Maior mudança desde {before}: {metric} piorou (percentil {a} → {b})",
    },
    "trend_title_same": {
        "en": "No big change since {before}: every percentile moved less than {t} points",
        "pt": "Sem grandes mudanças desde {before}: nenhum percentil mudou {t} pontos ou mais",
    },
    "trend_context": {
        "en": "{before}: {prev_club} ({prev_league}), {prev_min} min · {after}: {club} "
        "({league}), {min} min",
        "pt": "{before}: {prev_club} ({prev_league}), {prev_min} min · {after}: {club} "
        "({league}), {min} min",
    },
    "trend_how": {
        "en": "Each row is one metric. The grey dot is the player's percentile last season and "
        "the black dot this season, both against players of his position with at least {min} "
        "minutes in all leagues in scope (100 = best). A solid line marks a change of {t} points "
        "or more; a dotted line, a smaller move. Because 100 is always best, *improved* means "
        "better even where lower raw numbers are better: fewer cards, fewer goals conceded. "
        "Percentiles are relative: a player can rise because he improved or because his peers "
        "changed.",
        "pt": "Cada linha é uma métrica. O ponto cinzento é o percentil do jogador na época "
        "anterior e o preto nesta época, ambos face a jogadores da sua posição com pelo menos "
        "{min} minutos em todas as ligas analisadas (100 = melhor). Uma linha contínua marca uma "
        "mudança de {t} pontos ou mais; uma pontilhada, uma mudança menor. Como 100 é sempre o "
        "melhor, *melhorou* quer dizer melhor mesmo quando números mais baixos são melhores: "
        "menos cartões, menos golos sofridos. Os percentis são relativos: um jogador pode subir "
        "porque melhorou ou porque os pares mudaram.",
    },
    "trend_prev": {"en": "Last season", "pt": "Época anterior"},
    "trend_now": {"en": "This season", "pt": "Esta época"},
    "similar": {"en": "Find similar players", "pt": "Procurar jogadores parecidos"},
    "report": {"en": "Download one-page report", "pt": "Descarregar relatório de uma página"},
    "report_help": {
        "en": "A printable page with this player's key numbers, percentiles, change since last "
        "season, observations and data gaps. Open it in a browser and print or save as PDF.",
        "pt": "Uma página para imprimir com os números-chave, percentis, evolução, observações e "
        "lacunas dos dados deste jogador. Abra no navegador e imprima ou guarde como PDF.",
    },
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

insights = player_insights(
    row,
    confidence_minutes=thresholds,
    min_minutes=min_minutes,
    sample_thresholds=(
        settings.analysis.confidence_sample.medium,
        settings.analysis.confidence_sample.high,
    ),
)
# Season-over-season change, computed once for the page section and the report.
previous = trend.previous_season(data.players, row)
why_not = trend.minutes_note(previous, min_minutes, lang)
has_profile = row["minutes"] >= min_minutes and row["position_group"] in PROFILE_METRICS
changes = None
trend_insights: list = []
if has_profile and not why_not:
    changes = trend.season_changes(
        row,
        previous,
        PROFILE_METRICS[row["position_group"]],
        threshold=settings.analysis.trend_min_change,
    )
    trend_insights = trend.change_insights(
        changes, current=row, previous=previous, confidence_minutes=thresholds
    )
strength = data.league_strength[
    (data.league_strength["competition_id"] == row["competition_id"])
    & (data.league_strength["season"] == row["season"])
]["strength_index"]
strength_index = None if strength.empty else float(strength.iloc[0])

c.kpi_row(
    [
        c.Kpi(
            num(row["age"], lang, 1),
            tr(TEXT["age"], lang),
            tr(TEXT["age_note"], lang).format(year=int(row["season"]) + 1),
        ),
        c.Kpi(
            position_label(row["sub_position"], lang),
            tr(TEXT["position"], lang),
            tr(TEXT["position_note"], lang).format(
                group=POSITION_LABEL[lang][row["position_group"]]
            ),
        ),
        c.Kpi(str(row["club_name"]), tr(TEXT["club"], lang), str(row["competition_name"])),
        c.Kpi(
            num(row["minutes"], lang),
            tr(TEXT["minutes"], lang),
            tr(TEXT["minutes_note"], lang).format(
                share=float(row["minutes_share"]), conf=t(f"confidence_{confidence}", lang)
            ),
        ),
        c.Kpi(
            money(row["market_value_end"], lang),
            tr(TEXT["value"], lang),
            f"{tr(TEXT['contract'], lang)} "
            + ("—" if pd.isna(contract) else contract.date().isoformat()),
        ),
    ]
)

season_text = season_label(int(row["season"]))
report_html = player_report_html(
    ReportInput(
        row=row,
        profile_keys=list(PROFILE_METRICS.get(row["position_group"], ())) if has_profile else [],
        insights=insights,
        min_minutes=min_minutes,
        confidence=confidence,
        data_cutoff=data.data_cutoff,
        season_label=season_text,
        strength_index=strength_index,
        trend_insights=trend_insights,
        trend_note=why_not if has_profile else None,
        previous_season_label=(None if previous is None else season_label(int(previous["season"]))),
    ),
    lang,
)
report_col, list_col, _ = st.columns([1, 1, 1])
sl.toggle_button(row, lang, key="profile_shortlist", container=list_col)
report_col.download_button(
    tr(TEXT["report"], lang),
    data=report_html.encode("utf-8"),
    file_name=report_filename(row, season_text),
    mime="text/html",
    help=tr(TEXT["report_help"], lang),
    icon=":material/description:",
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

# Change since last season (percentiles against the same kind of peers each season)
st.subheader(tr(TEXT["trend_heading"], lang))
if not has_profile:
    st.caption(t("no_data", lang))
elif why_not:
    st.caption(why_not)
else:
    before, after = season_label(int(previous["season"])), season_label(int(row["season"]))
    threshold = f"{settings.analysis.trend_min_change:g}"
    top = changes.iloc[0]
    if top["direction"] == "same":
        trend_title = tr(TEXT["trend_title_same"], lang).format(before=before, t=threshold)
    else:
        trend_title = tr(TEXT[f"trend_title_{top['direction']}"], lang).format(
            before=before,
            metric=metric(top["metric"]).label_for(lang).lower(),
            a=round(top["previous_pct"]),
            b=round(top["current_pct"]),
        )
    st.caption(
        tr(TEXT["trend_context"], lang).format(
            before=before,
            prev_club=previous["club_name"],
            prev_league=previous["competition_name"],
            prev_min=num(previous["minutes"], lang),
            after=after,
            club=row["club_name"],
            league=row["competition_name"],
            min=num(row["minutes"], lang),
        )
    )
    c.chart_block(
        charts.season_change(changes, lang, title=trend_title, seasons=(before, after)),
        lang=lang,
        footer=c.source_note(lang, data_cutoff=data.data_cutoff),
        how_to_read=tr(TEXT["trend_how"], lang).format(min=num(min_minutes, lang), t=threshold),
        insights=trend_insights,
        observed=pd.DataFrame(
            {
                tr(TEXT["metric"], lang): [metric(k).label_for(lang) for k in changes["metric"]],
                tr(TEXT["trend_prev"], lang): changes["previous_pct"].round(0),
                tr(TEXT["trend_now"], lang): changes["current_pct"].round(0),
            }
        ),
        key="trend",
    )

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

ai_note_block(
    row,
    settings=settings,
    lang=lang,
    confidence=confidence,
    insights=insights,
    league_strength_index=strength_index,
)

c.unavailable_metrics(lang)
if st.button(tr(TEXT["similar"], lang), type="primary"):
    go_to("similar", row)
