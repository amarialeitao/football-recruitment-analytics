"""Plotly figures shared by several pages. Pure functions: data in, figure out."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from scouting.metrics.catalog import metric
from scouting.metrics.percentiles import PCT_SUFFIX
from scouting.ui.theme import ACCENT, BORDER, MUTED, NEUTRAL_SERIES, PRIMARY, PRIMARY_SOFT


def percentile_profile(
    row: pd.Series,
    keys: Sequence[str],
    lang: str,
    *,
    title: str,
    compare: pd.Series | None = None,
    names: tuple[str, str] | None = None,
) -> go.Figure:
    """Horizontal percentile bars (0-100) for ``keys``; optional second player for comparison.

    Bars run from 0 so their length is the percentile; a dotted line marks the median (50).
    The raw value of each metric is in the hover and the bar label.
    """
    labels = [metric(k).label_for(lang) for k in reversed(keys)]
    fig = go.Figure()

    def add(player: pd.Series, name: str, color: str, line: str | None = None) -> None:
        pct = [player.get(k + PCT_SUFFIX) for k in reversed(keys)]
        raw = [player.get(k) for k in reversed(keys)]
        text = ["—" if pd.isna(p) else f"{p:.0f}" for p in pct]
        fig.add_trace(
            go.Bar(
                x=[0 if pd.isna(p) else p for p in pct],
                y=labels,
                orientation="h",
                name=name,
                marker={"color": color, "line": {"color": line or color, "width": 1}},
                text=text,
                textposition="outside",
                customdata=[
                    "—" if pd.isna(v) else metric(k).fmt.format(float(v))
                    for k, v in zip(reversed(keys), raw, strict=True)
                ],
                hovertemplate="%{y}<br>Percentile %{x:.0f}<br>Value %{customdata}<extra></extra>",
            )
        )

    first, second = names or ("", "")
    add(row, first, PRIMARY)
    if compare is not None:
        add(compare, second, PRIMARY_SOFT, line=PRIMARY)
    fig.add_vline(
        x=50,
        line_dash="dot",
        line_color=MUTED,
        line_width=1,
        annotation_text="median" if lang == "en" else "mediana",
        annotation_position="top",
        annotation_font={"size": 11, "color": MUTED},
    )
    axis_title = (
        "Percentile vs players in the same position (100 = best)"
        if lang == "en"
        else "Percentil vs jogadores da mesma posição (100 = melhor)"
    )
    fig.update_layout(
        title=title,
        barmode="group",
        xaxis={"range": [0, 108], "title": axis_title},
        yaxis={"title": None},
        height=110 + 48 * len(keys) * (2 if compare is not None else 1),
        showlegend=compare is not None,
        bargap=0.25,
    )
    return fig


def value_trajectory(
    valuations: pd.DataFrame,
    lang: str,
    *,
    title: str,
    season: int,
) -> go.Figure:
    """Market value over time (step line), with the selected season shaded."""
    fig = go.Figure(
        go.Scatter(
            x=valuations["date"],
            y=valuations["market_value_in_eur"],
            mode="lines+markers",
            line={"shape": "hv", "color": PRIMARY, "width": 2},
            marker={"size": 6},
            hovertemplate="%{x|%Y-%m-%d}<br>€%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_vrect(
        x0=f"{season}-07-01",
        x1=f"{season + 1}-06-30",
        fillcolor=BORDER,
        opacity=0.5,
        line_width=0,
        annotation_text=f"{season}/{(season + 1) % 100:02d}",
        annotation_position="top left",
    )
    fig.update_layout(
        title=title,
        yaxis={"title": "€", "rangemode": "tozero", "tickformat": "~s"},
        xaxis={"title": None},
        height=320,
        showlegend=False,
    )
    return fig


def minutes_by_season(rows: pd.DataFrame, lang: str, *, title: str) -> go.Figure:
    """Minutes per season and competition, labelled with the share of team minutes."""
    ordered = rows.sort_values(["season", "competition_id"])
    x = [
        f"{s}/{(s + 1) % 100:02d} · {c}"
        for s, c in zip(ordered["season"], ordered["competition_name"], strict=True)
    ]
    fig = go.Figure(
        go.Bar(
            x=x,
            y=ordered["minutes"],
            marker={"color": [PRIMARY if m >= 900 else NEUTRAL_SERIES for m in ordered["minutes"]]},
            text=[f"{s:.0%}" for s in ordered["minutes_share"]],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:,} min<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        yaxis={"title": "Minutes" if lang == "en" else "Minutos", "rangemode": "tozero"},
        xaxis={"title": None},
        height=320,
        showlegend=False,
    )
    return fig


def highlight_color(is_highlight: bool) -> str:
    return ACCENT if is_highlight else NEUTRAL_SERIES
