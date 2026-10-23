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
from scouting.ui.i18n import LANGUAGES, Lang, num, t

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


def keep_widget_state() -> None:
    """Keep sidebar choices when moving between pages.

    Streamlit drops a widget's state when a page that does not render it runs; re-assigning the
    keys at the start of every run is the documented way to carry them across pages.
    """
    for key in list(st.session_state):
        if str(key).startswith(STATE_PREFIX) or key == "lang_selector":
            st.session_state[key] = st.session_state[key]


def language_selector() -> Lang:
    """EN / PT toggle at the top of the sidebar."""
    keep_widget_state()
    if "lang_selector" not in st.session_state:
        st.session_state["lang_selector"] = current_lang()
    choice = st.sidebar.segmented_control(
        t("language", current_lang()),
        options=list(LANGUAGES),
        format_func=LANGUAGES.get,
        key="lang_selector",
    )
    lang: Lang = choice or "en"
    st.session_state["lang"] = lang
    return lang


MAX_VALUE_OPTIONS: list[float | None] = [None, 0.5, 1, 2, 3, 5, 10, 20]


def _init_state(defaults: Filters) -> None:
    """Put default filter values in session state once; widgets then read only their key."""
    initial = {
        "season": defaults.season,
        "competitions": list(defaults.competitions),
        "positions": list(POSITION_ORDER),
        "age": (15, 45),
        "min_minutes": defaults.min_minutes,
        "max_value": None,
    }
    for name, value in initial.items():
        st.session_state.setdefault(STATE_PREFIX + name, value)


def sidebar_filters(
    df: pd.DataFrame, settings: Settings, *, show_value: bool = True
) -> tuple[Filters, pd.DataFrame, pd.DataFrame]:
    """Render the sidebar and return ``(filters, universe, selection)``."""
    lang = current_lang()
    seasons = sorted(df["season"].unique().tolist())
    defaults = default_filters(settings, seasons)
    _init_state(defaults)
    if st.session_state[STATE_PREFIX + "season"] not in seasons:
        st.session_state[STATE_PREFIX + "season"] = defaults.season
    names = settings.scope.competitions
    sb = st.sidebar
    sb.subheader(t("filters", lang))

    season = sb.selectbox(
        t("season", lang),
        seasons,
        format_func=lambda s: f"{s}/{(s + 1) % 100:02d}",
        key=STATE_PREFIX + "season",
    )
    competitions = sb.multiselect(
        t("leagues", lang),
        options=list(names),
        format_func=lambda c: names.get(c, c),
        key=STATE_PREFIX + "competitions",
    )
    positions = sb.pills(
        t("positions", lang),
        options=POSITION_ORDER,
        selection_mode="multi",
        format_func=lambda p: t(p, lang),
        key=STATE_PREFIX + "positions",
    )
    age_range = sb.slider(t("age", lang), 15, 45, key=STATE_PREFIX + "age")
    min_minutes = sb.slider(
        t("min_minutes", lang), 0, 3000, step=90, key=STATE_PREFIX + "min_minutes"
    )
    max_value = None
    if show_value:
        picked = sb.select_slider(
            t("max_value", lang),
            options=MAX_VALUE_OPTIONS,
            format_func=lambda v: t("no_limit", lang) if v is None else f"€{v:g}m",
            key=STATE_PREFIX + "max_value",
        )
        max_value = None if picked is None else float(picked) * 1e6

    sb.button(t("clear_filters", lang), on_click=_reset, width="stretch")

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
    sb.caption(f"{num(len(selection), lang)} {t('players_selected', lang)}")
    return filters, universe, selection
