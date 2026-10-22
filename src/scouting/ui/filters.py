"""Sidebar filters, shared by every page.

The sidebar returns two views of the data, for the same reason the comparisons need it:

* ``universe``: only the season filter applied. Percentiles and models were computed on the
  whole universe, so pages read reference values from here.
* ``selection``: every filter applied (leagues, positions, age, minutes, value). This is the
  shortlist the user is looking at.

Filtering never recomputes percentiles: a player's percentile does not change because the user
narrowed the list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from scouting.config import Settings
from scouting.ui.i18n import LANGUAGES, Lang, t

POSITION_ORDER = ["Forward", "Midfielder", "Defender", "Goalkeeper"]
STATE_PREFIX = "flt_"


@dataclass(frozen=True)
class Filters:
    season: int
    competitions: tuple[str, ...]
    positions: tuple[str, ...] = tuple(POSITION_ORDER)
    age_range: tuple[float, float] = (15.0, 45.0)
    min_minutes: int = 0
    max_market_value: float | None = None
    extra: dict = field(default_factory=dict)


def apply_filters(df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    """Rows matching every filter (pure function, used by the sidebar and the tests)."""
    mask = (
        (df["season"] == filters.season)
        & df["competition_id"].isin(filters.competitions)
        & df["position_group"].isin(filters.positions)
        & df["minutes"].ge(filters.min_minutes)
    )
    low, high = filters.age_range
    mask &= df["age"].between(low, high) | df["age"].isna()
    if filters.max_market_value is not None:
        mask &= df["market_value_end"].le(filters.max_market_value)
    return df[mask]


def default_filters(settings: Settings, seasons: list[int]) -> Filters:
    return Filters(
        season=max(seasons),
        competitions=tuple(settings.scope.competition_ids),
        min_minutes=settings.analysis.min_minutes,
    )


def current_lang() -> Lang:
    return st.session_state.get("lang", "en")


def _reset() -> None:
    for key in [k for k in st.session_state if str(k).startswith(STATE_PREFIX)]:
        del st.session_state[key]
    st.session_state["lang"] = current_lang()


def language_selector() -> Lang:
    """EN / PT toggle at the top of the sidebar."""
    choice = st.sidebar.segmented_control(
        t("language", current_lang()),
        options=list(LANGUAGES),
        format_func=LANGUAGES.get,
        default=current_lang(),
        key="lang_selector",
    )
    lang: Lang = choice or "en"
    st.session_state["lang"] = lang
    return lang


def sidebar_filters(
    df: pd.DataFrame, settings: Settings, *, show_value: bool = True
) -> tuple[Filters, pd.DataFrame, pd.DataFrame]:
    """Render the sidebar and return ``(filters, universe, selection)``."""
    lang = current_lang()
    seasons = sorted(df["season"].unique().tolist())
    defaults = default_filters(settings, seasons)
    names = settings.scope.competitions
    sb = st.sidebar
    sb.subheader(t("filters", lang))

    season = sb.selectbox(
        t("season", lang),
        seasons,
        index=seasons.index(defaults.season),
        format_func=lambda s: f"{s}/{(s + 1) % 100:02d}",
        key=STATE_PREFIX + "season",
    )
    competitions = sb.multiselect(
        t("leagues", lang),
        options=list(names),
        default=list(defaults.competitions),
        format_func=lambda c: names.get(c, c),
        key=STATE_PREFIX + "competitions",
    )
    positions = sb.pills(
        t("positions", lang),
        options=POSITION_ORDER,
        default=POSITION_ORDER,
        selection_mode="multi",
        format_func=lambda p: t(p, lang),
        key=STATE_PREFIX + "positions",
    )
    age_range = sb.slider(t("age", lang), 15, 45, (15, 45), key=STATE_PREFIX + "age")
    min_minutes = sb.slider(
        t("min_minutes", lang),
        0,
        3000,
        defaults.min_minutes,
        step=90,
        key=STATE_PREFIX + "min_minutes",
    )
    max_value = None
    if show_value:
        options = [None, 0.5, 1, 2, 3, 5, 10, 20]
        picked = sb.select_slider(
            t("max_value", lang),
            options=options,
            value=None,
            format_func=lambda v: t("no_limit", lang) if v is None else f"€{v:g}m",
            key=STATE_PREFIX + "max_value",
        )
        max_value = None if picked is None else float(picked) * 1e6

    sb.button(
        t("clear_filters", lang),
        on_click=_reset,
        width="stretch",
    )

    filters = Filters(
        season=int(season),
        competitions=tuple(competitions),
        positions=tuple(positions or ()),
        age_range=(float(age_range[0]), float(age_range[1])),
        min_minutes=int(min_minutes),
        max_market_value=max_value,
    )
    universe = df[df["season"] == filters.season]
    selection = apply_filters(df, filters)
    sb.caption(f"{len(selection):,} {t('players_selected', lang)}")
    return filters, universe, selection
