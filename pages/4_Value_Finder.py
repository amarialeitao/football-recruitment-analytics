"""Value Finder: output compared with market value, to spot undervalued profiles."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scouting.insights import POSITION_LABEL
from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui.data import setup_page
from scouting.ui.filters import POSITION_ORDER, language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label, t
from scouting.ui.players import confidence_for_minutes, go_to, money, season_label, tr
from scouting.ui.theme import ACCENT, NEUTRAL_SERIES

TEXT = {
    "title": {"en": "Value Finder", "pt": "Valor de mercado"},
    "question": {
        "en": "Who gives the most output for the money?",
        "pt": "Quem dá mais rendimento pelo dinheiro?",
    },
    "group": {"en": "Position group", "pt": "Grupo de posição"},
    "threshold": {
        "en": "Flag players valued at or below this share of the expected value",
        "pt": "Destacar jogadores avaliados até esta fração do valor esperado",
    },
    "analysed": {"en": "{pos} compared", "pt": "{pos} comparados"},
    "analysed_note": {
        "en": "match your filters and have an up-to-date value",
        "pt": "cumprem os filtros e têm valor atualizado",
    },
    "flagged": {
        "en": "valued at {p:.0%} or less of what their output usually costs",
        "pt": "avaliados em {p:.0%} ou menos do que a sua produção costuma custar",
    },
    "flagged_note": {"en": "listed in the table below", "pt": "na tabela abaixo"},
    "median_ratio": {
        "en": "typical value vs expected",
        "pt": "valor vs esperado típico",
    },
    "median_ratio_note": {
        "en": "1.00x = priced exactly as the model expects",
        "pt": "1,00x = preço exatamente como o modelo espera",
    },
    "fit": {"en": "model fit (R²)", "pt": "ajuste do modelo (R²)"},
    "fit_note": {
        "en": "output, age and league explain {p:.0%} of the differences in value",
        "pt": "produção, idade e liga explicam {p:.0%} das diferenças de valor",
    },
    "chart_title": {
        "en": "{k} of {n} {pos} are valued at or below {p:.0%} of what similar output "
        "usually costs",
        "pt": "{k} de {n} {pos} estão avaliados em até {p:.0%} do que costuma custar uma "
        "produção parecida",
    },
    "x": {"en": "Performance score (mean profile percentile)", "pt": "Índice de rendimento"},
    "y": {"en": "Market value (€, log scale)", "pt": "Valor de mercado (€, escala log)"},
    "flagged_legend": {"en": "Below threshold", "pt": "Abaixo do limite"},
    "others": {"en": "Others", "pt": "Outros"},
    "how": {
        "en": "Horizontal axis: performance score, the average of the player's profile "
        "percentiles ({metrics}). Vertical axis: end-of-season market value. Expected value comes "
        "from a fit, within the position group, of market value on performance score, age and "
        "league strength. Highlighted players are valued well below what that fit predicts. "
        "Market value is a crowd estimate, not a fee; values older than a year are excluded.",
        "pt": "Eixo horizontal: índice de rendimento, a média dos percentis do perfil do jogador "
        "({metrics}). Eixo vertical: valor de mercado no fim da época. O valor esperado vem de um "
        "ajuste, dentro do grupo de posição, do valor de mercado sobre rendimento, idade e força "
        "da liga. Os jogadores destacados valem bem menos do que esse ajuste prevê. Valor de "
        "mercado é uma estimativa, não um preço; valores com mais de um ano ficam de fora.",
    },
    "none": {
        "en": "No player in this group has a fitted value with the current filters.",
        "pt": "Nenhum jogador deste grupo tem valor ajustado com os filtros atuais.",
    },
    "table_caption": {
        "en": "Flagged players, cheapest relative to output first. Select a row to open the "
        "profile.",
        "pt": "Jogadores destacados, do mais barato face ao rendimento para o mais caro. "
        "Selecione uma linha para abrir o perfil.",
    },
    "open": {"en": "Open profile", "pt": "Abrir perfil"},
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "league": {"en": "League", "pt": "Liga"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "score": {"en": "Performance score", "pt": "Índice de rendimento"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "expected": {"en": "Expected value", "pt": "Valor esperado"},
    "ratio": {"en": "Value vs expected", "pt": "Valor vs esperado"},
    "confidence": {"en": "Confidence", "pt": "Confiança"},
}

settings, data = setup_page("Value Finder")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))

groups = [g for g in POSITION_ORDER if g in filters.positions] or POSITION_ORDER
col1, col2 = st.columns([1, 2])
group = col1.selectbox(tr(TEXT["group"], lang), groups, format_func=lambda g: t(g, lang))
threshold = col2.slider(tr(TEXT["threshold"], lang), 0.3, 1.0, 0.5, 0.05, format="percent")

pool = selection[
    (selection["position_group"] == group)
    & selection["value_ratio"].notna()
    & ~selection["market_value_stale"].fillna(True).astype(bool)
]
if pool.empty:
    st.info(tr(TEXT["none"], lang))
    st.stop()

flagged = pool[pool["value_ratio"] <= threshold].sort_values("value_ratio")
fit_r2 = pool["fit_r2"].dropna()
c.kpi_row(
    [
        c.Kpi(
            num(len(pool), lang),
            tr(TEXT["analysed"], lang).format(pos=POSITION_LABEL[lang][group]),
            tr(TEXT["analysed_note"], lang),
        ),
        c.Kpi(
            num(len(flagged), lang),
            tr(TEXT["flagged"], lang).format(p=threshold),
            tr(TEXT["flagged_note"], lang),
        ),
        c.Kpi(
            num(pool["value_ratio"].median(), lang, 2) + "x",
            tr(TEXT["median_ratio"], lang),
            tr(TEXT["median_ratio_note"], lang),
        ),
        c.Kpi(
            "—" if fit_r2.empty else num(fit_r2.iloc[0], lang, 2),
            tr(TEXT["fit"], lang),
            "" if fit_r2.empty else tr(TEXT["fit_note"], lang).format(p=float(fit_r2.iloc[0])),
        ),
    ]
)

is_flagged = pool["value_ratio"] <= threshold
fig = go.Figure()
for mask, name, color, size in (
    (~is_flagged, tr(TEXT["others"], lang), NEUTRAL_SERIES, 7),
    (is_flagged, tr(TEXT["flagged_legend"], lang), ACCENT, 10),
):
    part = pool[mask]
    fig.add_trace(
        go.Scatter(
            x=part["performance_score"],
            y=part["market_value_end"],
            mode="markers",
            name=name,
            marker={"color": color, "size": size, "opacity": 0.85, "line": {"width": 0}},
            customdata=part[["name", "club_name", "competition_name", "expected_market_value"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} (%{customdata[2]})<br>"
                "Score %{x:.0f} · €%{y:,.0f}<br>Expected €%{customdata[3]:,.0f}<extra></extra>"
            ),
        )
    )
fig.update_layout(
    title=tr(TEXT["chart_title"], lang).format(
        k=len(flagged), n=len(pool), pos=POSITION_LABEL[lang][group], p=threshold
    ),
    xaxis={"title": tr(TEXT["x"], lang), "range": [0, 100]},
    yaxis={
        "title": tr(TEXT["y"], lang),
        "type": "log",
        "tickvals": [1e4, 1e5, 1e6, 1e7, 1e8],
        "ticktext": ["€10k", "€100k", "€1m", "€10m", "€100m"],
        "minor": {"showgrid": False},
    },
    height=480,
)
c.chart_block(
    fig,
    lang=lang,
    footer=c.source_note(
        lang,
        data_cutoff=data.data_cutoff,
        season_label=season_label(filters.season),
        population=f"{t(group, lang)} · {num(filters.min_minutes, lang)}+ min",
    ),
    how_to_read=tr(TEXT["how"], lang).format(
        metrics=", ".join(metric(k).label_for(lang) for k in PROFILE_METRICS[group])
    ),
    key="value",
)

if flagged.empty:
    st.stop()

thresholds = (
    settings.analysis.confidence_minutes.medium,
    settings.analysis.confidence_minutes.high,
)
table = pd.DataFrame(
    {
        # The answer first (how cheap, for what output), then who and where.
        tr(TEXT["name"], lang): flagged["name"],
        tr(TEXT["ratio"], lang): flagged["value_ratio"],
        tr(TEXT["value"], lang): flagged["market_value_end"],
        tr(TEXT["expected"], lang): flagged["expected_market_value"],
        tr(TEXT["score"], lang): flagged["performance_score"],
        tr(TEXT["club"], lang): flagged["club_name"],
        tr(TEXT["league"], lang): flagged["competition_name"],
        tr(TEXT["position"], lang): flagged["sub_position"].map(lambda p: position_label(p, lang)),
        tr(TEXT["age"], lang): flagged["age"],
        tr(TEXT["minutes"], lang): flagged["minutes"],
        tr(TEXT["confidence"], lang): [
            t(f"confidence_{confidence_for_minutes(m, thresholds)}", lang)
            for m in flagged["minutes"]
        ],
    }
).reset_index(drop=True)
st.caption(tr(TEXT["table_caption"], lang))
event = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        tr(TEXT["name"], lang): st.column_config.TextColumn(pinned=True),
        tr(TEXT["age"], lang): st.column_config.NumberColumn(format="%.1f"),
        tr(TEXT["score"], lang): col.number("performance_score", lang, "%.0f"),
        tr(TEXT["value"], lang): col.money("market_value", lang, tr(TEXT["value"], lang)),
        tr(TEXT["expected"], lang): col.money("expected_value", lang, tr(TEXT["expected"], lang)),
        tr(TEXT["ratio"], lang): col.number("value_ratio", lang, "%.2fx"),
        tr(TEXT["confidence"], lang): col.text(
            "confidence", lang, medium=thresholds[0], high=thresholds[1]
        ),
    },
)
rows = event.selection.rows if event and event.selection else []
if rows:
    chosen = flagged.iloc[rows[0]]
    label = (
        f"{tr(TEXT['open'], lang)}: {chosen['name']} ({money(chosen['market_value_end'], lang)})"
    )
    if st.button(label, type="primary"):
        go_to("profile", chosen)
