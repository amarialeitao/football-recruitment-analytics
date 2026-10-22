"""Reusable page blocks: header, KPI cards, insights, chart block, status board, footer.

Components only render what they receive. Text comes from :mod:`scouting.ui.i18n` or from
:class:`scouting.insights.Insight`; colours come from :mod:`scouting.ui.theme`.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scouting.health import STATUS_LABEL, StatusItem
from scouting.insights import Insight, sort_insights
from scouting.metrics.catalog import UNAVAILABLE_METRICS
from scouting.ui.i18n import Lang, t
from scouting.ui.theme import CONFIDENCE_COLORS, STATUS_COLORS

OBSERVATION_MARKER = "▪"
INTERPRETATION_MARKER = "◆"


@dataclass(frozen=True)
class Kpi:
    value: str
    label: str
    note: str | None = None


def page_header(title: str, question: str) -> None:
    """Page title plus the recruitment question the page answers."""
    st.title(title)
    st.markdown(f'<div class="sc-question">{html.escape(question)}</div>', unsafe_allow_html=True)


def kpi_html(items: Sequence[Kpi]) -> str:
    cards = []
    for item in items:
        note = f'<div class="sc-kpi-note">{html.escape(item.note)}</div>' if item.note else ""
        cards.append(
            '<div class="sc-kpi">'
            f'<div class="sc-kpi-value">{html.escape(item.value)}</div>'
            f'<div class="sc-kpi-label">{html.escape(item.label)}</div>{note}</div>'
        )
    return f'<div class="sc-kpi-grid">{"".join(cards)}</div>'


def kpi_row(items: Sequence[Kpi]) -> None:
    st.markdown(kpi_html(items), unsafe_allow_html=True)


def confidence_badge(level: str, lang: Lang) -> str:
    color = CONFIDENCE_COLORS[level]
    label = t(f"confidence_{level}", lang)
    return f'<span class="sc-badge" style="color:{color}">{label}</span>'


def insight_html(insight: Insight, lang: Lang) -> str:
    marker = OBSERVATION_MARKER if insight.kind == "observation" else INTERPRETATION_MARKER
    return (
        f'<div class="sc-insight"><span class="sc-insight-marker">{marker}</span>'
        f"{html.escape(insight.render(lang))}{confidence_badge(insight.confidence, lang)}</div>"
    )


def insight_list(insights: Iterable[Insight], lang: Lang) -> None:
    ordered = sort_insights(insights)
    if not ordered:
        return
    st.markdown("".join(insight_html(i, lang) for i in ordered), unsafe_allow_html=True)


def source_note(
    lang: Lang,
    *,
    data_cutoff: pd.Timestamp,
    season_label: str | None = None,
    population: str | None = None,
) -> str:
    """Footer for every chart: source, season, cut-off date and population."""
    parts = [f"{t('source', lang)}: transfermarkt-datasets (CC0)"]
    if season_label:
        parts.append(f"{t('season', lang)} {season_label}")
    parts.append(f"{t('data_to', lang)} {data_cutoff.date().isoformat()}")
    if population:
        parts.append(population)
    return " · ".join(parts)


def chart_block(
    fig: go.Figure,
    *,
    lang: Lang,
    footer: str,
    how_to_read: str | None = None,
    insights: Iterable[Insight] = (),
    observed: pd.DataFrame | None = None,
    key: str | None = None,
) -> None:
    """Card with the chart, 'how to read', source footer, insights and observed data."""
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})
        if how_to_read:
            with st.popover(t("how_to_read", lang)):
                st.markdown(how_to_read)
        st.caption(footer)
        insights = list(insights)
        if insights:
            st.markdown(f"**{t('key_observations', lang)}**")
            insight_list(insights, lang)
        if observed is not None and not observed.empty:
            with st.expander(t("observed_data", lang)):
                st.dataframe(observed, hide_index=True, width="stretch")


def status_board_html(items: Sequence[StatusItem], lang: Lang) -> str:
    cards = []
    for item in items:
        color = STATUS_COLORS[item.status]
        cards.append(
            f'<div class="sc-status" style="border-left-color:{color}">'
            f'<div class="sc-status-head"><span>{html.escape(item.area[lang])}</span>'
            f'<span style="color:{color}">{STATUS_LABEL[lang][item.status]}</span></div>'
            f'<div class="sc-status-reason">{html.escape(item.reason[lang])}</div></div>'
        )
    return f'<div class="sc-status-grid">{"".join(cards)}</div>'


def status_board(items: Sequence[StatusItem], lang: Lang) -> None:
    st.subheader(t("status_board", lang))
    st.markdown(status_board_html(items, lang), unsafe_allow_html=True)


def unavailable_metrics(lang: Lang) -> None:
    """The metrics a recruiter would want that public data does not provide."""
    items = "".join(f"<li>{html.escape(m[lang])}</li>" for m in UNAVAILABLE_METRICS)
    st.markdown(
        f'<div class="sc-unavailable"><strong>{t("not_available", lang)}</strong>'
        f"<p>{t('not_available_note', lang)}</p><ul>{items}</ul></div>",
        unsafe_allow_html=True,
    )
