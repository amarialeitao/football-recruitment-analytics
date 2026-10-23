"""Potential: observable signals for young players (signals, not predictions)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scouting.metrics.potential import STRONG_PERCENTILE, STRONG_VALUE_GROWTH, potential_signals
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui.data import setup_page
from scouting.ui.filters import apply_filters, language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label
from scouting.ui.players import go_to, season_label, tr
from scouting.ui.theme import ACCENT, NEUTRAL_SERIES, PRIMARY, PRIMARY_SOFT

TEXT = {
    "title": {"en": "Potential", "pt": "Potencial"},
    "question": {
        "en": "Which young players are already trusted by their coaches?",
        "pt": "Que jogadores jovens já têm a confiança dos treinadores?",
    },
    "young": {"en": "Young players (≤ {age})", "pt": "Jogadores jovens (≤ {age})"},
    "two_plus": {"en": "Meet 2+ of 3 signals", "pt": "Cumprem 2+ de 3 sinais"},
    "median_share": {"en": "Median share of team minutes", "pt": "% mediana dos minutos da equipa"},
    "chart_title": {
        "en": "{k} players aged {age} or under meet at least two of the three signals",
        "pt": "{k} jogadores com {age} anos ou menos cumprem pelo menos dois dos três sinais",
    },
    "x": {"en": "Age", "pt": "Idade"},
    "y": {
        "en": "Share of team minutes, percentile vs same age and position",
        "pt": "% dos minutos da equipa, percentil vs mesma idade e posição",
    },
    "signals": {"en": "{n} signals", "pt": "{n} sinais"},
    "signal_one": {"en": "1 signal", "pt": "1 sinal"},
    "how": {
        "en": "Each dot is a young player. Height: how much he plays compared with regulars "
        "(players above the minimum minutes) of the same age and position group (percentile, "
        "100 = plays the most). The three signals are: "
        "minutes for his age in the top {p:.0f}%, start rate for his age in the top {p:.0f}%, "
        "and market value up at least {g:.0%} over the season. Age bands with fewer than five "
        "players get no percentile.",
        "pt": "Cada ponto é um jogador jovem. Altura: quanto joga face a titulares habituais "
        "(acima do mínimo de minutos) da mesma idade e grupo de posição (percentil, 100 = joga "
        "mais). Os três sinais são: minutos para a "
        "idade no top {p:.0f}%, titularidades para a idade no top {p:.0f}%, e valor de mercado a "
        "subir pelo menos {g:.0%} na época. Faixas etárias com menos de cinco jogadores ficam "
        "sem percentil.",
    },
    "limits": {
        "en": "**Read as signals, not predictions.** Playing time and market value are public "
        "proxies for how clubs rate a young player; they do not measure ability. Only the "
        "seasons in scope are included, so earlier development is not visible.",
        "pt": "**Leia como sinais, não previsões.** Minutos e valor de mercado são indicadores "
        "públicos de como os clubes avaliam um jovem; não medem a qualidade. Só as épocas "
        "analisadas estão incluídas, por isso o desenvolvimento anterior não é visível.",
    },
    "none": {
        "en": "No young players match the current filters.",
        "pt": "Nenhum jogador jovem corresponde aos filtros atuais.",
    },
    "table_caption": {
        "en": "Young players, strongest signals first. Select a row to open the profile.",
        "pt": "Jogadores jovens, sinais mais fortes primeiro. Selecione uma linha para abrir o "
        "perfil.",
    },
    "open": {"en": "Open profile", "pt": "Abrir perfil"},
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "league": {"en": "League", "pt": "Liga"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "share": {"en": "Share of team minutes", "pt": "% dos minutos da equipa"},
    "min_pct": {
        "en": "Minutes vs same age (percentile)",
        "pt": "Minutos vs mesma idade (percentil)",
    },
    "start_pct": {
        "en": "Starts vs same age (percentile)",
        "pt": "Titularidades vs mesma idade (percentil)",
    },
    "growth": {"en": "Value change in season", "pt": "Variação do valor na época"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "n_signals": {"en": "Signals", "pt": "Sinais"},
}

SIGNAL_COLORS = {0: NEUTRAL_SERIES, 1: PRIMARY_SOFT, 2: PRIMARY, 3: ACCENT}

settings, data = setup_page("Potential")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))
st.markdown(tr(TEXT["limits"], lang))

max_age = settings.analysis.young_age_max
# Signals compare each player with regulars of the same age band in the season (universe),
# then the sidebar filters choose which young players are shown.
signals = potential_signals(
    universe, young_age_max=max_age, min_minutes=settings.analysis.min_minutes
)
shown = apply_filters(signals, filters)
if shown.empty:
    st.info(tr(TEXT["none"], lang))
    st.stop()

strong = shown[shown["signals_met"] >= 2]
c.kpi_row(
    [
        c.Kpi(
            num(len(shown), lang),
            tr(TEXT["young"], lang).format(age=f"{max_age:g}"),
            season_label(filters.season),
        ),
        c.Kpi(num(len(strong), lang), tr(TEXT["two_plus"], lang)),
        c.Kpi(f"{shown['minutes_share'].median():.0%}", tr(TEXT["median_share"], lang)),
    ]
)

fig = go.Figure()
for n in range(4):
    part = shown[shown["signals_met"] == n]
    if part.empty:
        continue
    fig.add_trace(
        go.Scatter(
            x=part["age"],
            y=part["minutes_for_age_pct"],
            mode="markers",
            name=tr(TEXT["signal_one"], lang) if n == 1 else tr(TEXT["signals"], lang).format(n=n),
            marker={
                "color": SIGNAL_COLORS[n],
                "size": 6 + 3 * n,
                "line": {"width": 1 if n == 1 else 0, "color": PRIMARY},
                "opacity": 0.9,
            },
            customdata=part[["name", "club_name", "competition_name", "minutes"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} (%{customdata[2]})<br>"
                "Age %{x:.1f} · %{customdata[3]:,} min<br>Percentile %{y:.0f}<extra></extra>"
            ),
        )
    )
fig.add_hline(y=STRONG_PERCENTILE, line_dash="dot", line_color=NEUTRAL_SERIES, line_width=1)
fig.update_layout(
    title=tr(TEXT["chart_title"], lang).format(k=len(strong), age=f"{max_age:g}"),
    xaxis={"title": tr(TEXT["x"], lang)},
    yaxis={"title": tr(TEXT["y"], lang), "range": [0, 105]},
    height=460,
)
c.chart_block(
    fig,
    lang=lang,
    footer=c.source_note(
        lang,
        data_cutoff=data.data_cutoff,
        season_label=season_label(filters.season),
        population=f"≤ {max_age:g} · {num(filters.min_minutes, lang)}+ min",
    ),
    how_to_read=tr(TEXT["how"], lang).format(p=100 - STRONG_PERCENTILE, g=STRONG_VALUE_GROWTH),
    key="potential",
)

ordered = shown.reset_index(drop=True)
table = pd.DataFrame(
    {
        tr(TEXT["name"], lang): ordered["name"],
        tr(TEXT["club"], lang): ordered["club_name"],
        tr(TEXT["league"], lang): ordered["competition_name"],
        tr(TEXT["position"], lang): ordered["sub_position"].map(lambda p: position_label(p, lang)),
        tr(TEXT["age"], lang): ordered["age"],
        tr(TEXT["n_signals"], lang): ordered["signals_met"],
        tr(TEXT["share"], lang): ordered["minutes_share"],
        tr(TEXT["min_pct"], lang): ordered["minutes_for_age_pct"],
        tr(TEXT["start_pct"], lang): ordered["start_rate_for_age_pct"],
        tr(TEXT["growth"], lang): ordered["value_growth"],
        tr(TEXT["value"], lang): ordered["market_value_end"],
    }
)
st.caption(tr(TEXT["table_caption"], lang))
event = st.dataframe(
    col.as_percent(table, [tr(TEXT["share"], lang), tr(TEXT["growth"], lang)]),
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        tr(TEXT["name"], lang): st.column_config.TextColumn(pinned=True),
        tr(TEXT["age"], lang): st.column_config.NumberColumn(format="%.1f"),
        tr(TEXT["n_signals"], lang): col.number("signals", lang, "%d"),
        tr(TEXT["share"], lang): col.share("minutes_share", lang),
        tr(TEXT["min_pct"], lang): col.number("minutes_for_age", lang, "%.0f"),
        tr(TEXT["start_pct"], lang): col.number("starts_for_age", lang, "%.0f"),
        tr(TEXT["growth"], lang): col.number("value_growth", lang, "%+.0f%%"),
        tr(TEXT["value"], lang): col.money("market_value", lang, tr(TEXT["value"], lang)),
    },
)
rows = event.selection.rows if event and event.selection else []
if rows:
    chosen = ordered.iloc[rows[0]]
    if st.button(f"{tr(TEXT['open'], lang)}: {chosen['name']}", type="primary"):
        go_to("profile", chosen)
