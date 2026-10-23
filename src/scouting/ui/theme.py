"""Visual theme in Casa Pia's colours: black and white, with red as the single accent.

Colours are defined once here and used by the CSS, the charts and the components
(``.streamlit/config.toml`` mirrors them for Streamlit's own widgets). Red is kept for
highlights (the focus league, the flagged or reference player), black for the main series and
greys for everyone else. Status and confidence colours are separate and always come with a
text label, never alone. Contrast was checked against WCAG AA (red on white 5.2:1).
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

INK = "#141414"  # near-black: text and the main series
MUTED = "#5C5C5C"
BORDER = "#E3E3E3"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F5F5F5"

PRIMARY = INK  # the main series and the selected player
PRIMARY_SOFT = "#D4D4D4"  # second player in comparisons
ACCENT = "#D2261C"  # Casa Pia red, darkened from the crest's #FC3224 for legible contrast
NEUTRAL_SERIES = "#B5B5B5"  # everyone else

OK = "#2E7D5B"
ATTENTION = "#B7791F"
CRITICAL = "#9B1C1C"

CONFIDENCE_COLORS = {"high": OK, "medium": ATTENTION, "low": MUTED}
STATUS_COLORS = {"ok": OK, "attention": ATTENTION}

# Categorical palette: black, red, then greys (distinguishable by lightness as well as hue).
CATEGORICAL = [
    INK,
    ACCENT,
    "#9A9A9A",
    "#5C5C5C",
    "#E8857F",
    "#C9C9C9",
    "#8C1A13",
    "#3D3D3D",
]

# Ordered series such as seasons: oldest lightest, most recent black (no red: nothing to flag).
SEQUENTIAL_GREYS = ["#D4D4D4", "#9A9A9A", "#5C5C5C", INK]


def sequential_shades(n: int) -> list[str]:
    """``n`` shades from light to black, ending on black for the most recent item."""
    return SEQUENTIAL_GREYS[-n:] if n <= len(SEQUENTIAL_GREYS) else [INK] * n


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
    border-left: 3px solid {ACCENT}; padding-left: 0.75rem;
  }}
  [data-testid="stHeader"] {{ border-top: 4px solid {INK}; }}
  [data-testid="stSidebar"] {{ border-right: 4px solid {ACCENT}; }}
  .sc-disclaimer {{ font-size: 0.72rem; opacity: 0.75; margin-top: 1.5rem; line-height: 1.4; }}
  .sc-kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin: 0.5rem 0 1rem 0;
  }}
  .sc-kpi {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
    border-top: 3px solid {INK}; padding: 14px 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
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
    margin-bottom: 1.25rem;
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
