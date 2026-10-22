"""Neutral visual theme: colour tokens, CSS and a Plotly template.

Colours are defined once here and used by the CSS, the charts and the components. Status and
confidence colours always come with a text label, never alone.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

INK = "#1F2933"
MUTED = "#52606D"
BORDER = "#E4E7EB"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F5F7FA"

PRIMARY = "#2F6F8F"  # steel blue: the main series and the selected player
PRIMARY_SOFT = "#D6E6EE"
ACCENT = "#C8742B"  # amber: highlights only (the reference player, the focus league)
NEUTRAL_SERIES = "#9AA5B1"  # everyone else

OK = "#2E7D5B"
ATTENTION = "#B7791F"
CRITICAL = "#B23B3B"

CONFIDENCE_COLORS = {"high": OK, "medium": ATTENTION, "low": MUTED}
STATUS_COLORS = {"ok": OK, "attention": ATTENTION}

# Categorical palette (distinguishable for common colour-vision deficiencies).
CATEGORICAL = [
    "#2F6F8F",
    "#C8742B",
    "#5B8C5A",
    "#8E6C8A",
    "#B8A04B",
    "#4C7A9E",
    "#A0522D",
    "#6B7B8C",
]

FONT_FAMILY = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

TEMPLATE_NAME = "scouting"


def plotly_template() -> go.layout.Template:
    """Plotly template matching the app theme."""
    return go.layout.Template(
        layout=go.Layout(
            font={"family": FONT_FAMILY, "size": 13, "color": INK},
            colorway=CATEGORICAL,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            margin={"l": 48, "r": 16, "t": 48, "b": 40},
            title={"font": {"size": 16, "color": INK}, "x": 0, "xanchor": "left"},
            xaxis={"gridcolor": BORDER, "zerolinecolor": BORDER, "linecolor": BORDER},
            yaxis={"gridcolor": BORDER, "zerolinecolor": BORDER, "linecolor": BORDER},
            legend={"orientation": "h", "y": -0.2, "x": 0},
            hoverlabel={"font": {"family": FONT_FAMILY}},
        )
    )


def register_plotly_template() -> None:
    """Register the template and make it the default for every figure."""
    pio.templates[TEMPLATE_NAME] = plotly_template()
    pio.templates.default = TEMPLATE_NAME


CSS = f"""
<style>
  .block-container {{ padding-top: 2rem; max-width: 1200px; }}
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
  .sc-question {{
    color: {MUTED}; font-size: 1.05rem; margin: -0.4rem 0 1.2rem 0;
    border-left: 3px solid {PRIMARY}; padding-left: 0.75rem;
  }}
  .sc-kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin: 0.5rem 0 1rem 0;
  }}
  .sc-kpi {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 14px 16px; box-shadow: 0 1px 2px rgba(31, 41, 51, 0.04);
  }}
  .sc-kpi-value {{ font-size: 1.6rem; font-weight: 650; color: {INK}; line-height: 1.2; }}
  .sc-kpi-label {{ font-size: 0.8rem; color: {MUTED}; margin-top: 2px; }}
  .sc-kpi-note {{ font-size: 0.75rem; color: {MUTED}; margin-top: 6px; }}
  .sc-badge {{
    display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 1px 8px;
    border-radius: 999px; border: 1px solid currentColor; margin-left: 6px;
    vertical-align: middle; white-space: nowrap;
  }}
  .sc-insight {{ margin: 0.25rem 0 0.5rem 0; line-height: 1.45; }}
  .sc-insight-marker {{ color: {PRIMARY}; margin-right: 6px; }}
  .sc-status-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;
  }}
  .sc-status {{
    border: 1px solid {BORDER}; border-left-width: 4px; border-radius: 8px; padding: 10px 12px;
    background: {SURFACE};
  }}
  .sc-status-head {{
    font-weight: 600; color: {INK}; display: flex; justify-content: space-between;
  }}
  .sc-status-reason {{ font-size: 0.85rem; color: {MUTED}; margin-top: 4px; }}
  .sc-unavailable {{
    background: {SURFACE_ALT}; border: 1px dashed {BORDER}; border-radius: 8px;
    padding: 10px 14px; color: {MUTED}; font-size: 0.88rem;
  }}
</style>
"""
