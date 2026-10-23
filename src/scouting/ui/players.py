"""Shared page helpers: player labels, the remembered player selection and page links.

The selected player is kept in ``st.session_state`` as ``(player_id, season, competition_id)``
so moving from Player Finder to Profile to Similar Players keeps the same player.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import streamlit as st

from scouting.insights import confidence_from_sample, format_money
from scouting.ui.i18n import Lang, t

SELECTED_KEY = "selected_player"
KEY_COLUMNS = ("player_id", "season", "competition_id")

PAGES = {
    "overview": "pages/0_Market_Overview.py",
    "finder": "pages/1_Player_Finder.py",
    "profile": "pages/2_Player_Profile.py",
    "similar": "pages/3_Similar_Players.py",
    "value": "pages/4_Value_Finder.py",
    "potential": "pages/5_Potential.py",
    "quality": "pages/6_Data_Quality.py",
    "shortlist": "pages/7_Shortlist.py",
}


def tr(texts: Mapping[str, str], lang: Lang) -> str:
    """Pick the text for ``lang`` from a ``{"en": ..., "pt": ...}`` mapping."""
    return texts[lang]


def season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


def player_label(row: pd.Series) -> str:
    """'Name · Club (League) · 2025/26'."""
    club = row.get("club_name") or "—"
    league = row.get("competition_name") or row.get("competition_id")
    return f"{row['name']} · {club} ({league}) · {season_label(int(row['season']))}"


def player_key(row: pd.Series) -> tuple[int, int, str]:
    return int(row["player_id"]), int(row["season"]), str(row["competition_id"])


def remember_player(row: pd.Series) -> None:
    st.session_state[SELECTED_KEY] = player_key(row)


def find_row(df: pd.DataFrame, key: tuple[int, int, str] | None) -> pd.Series | None:
    if key is None:
        return None
    player_id, season, competition = key
    rows = df[
        (df["player_id"] == player_id)
        & (df["season"] == season)
        & (df["competition_id"] == competition)
    ]
    return None if rows.empty else rows.iloc[0]


def player_selector(
    candidates: pd.DataFrame,
    lang: Lang,
    *,
    label: str,
    prefer_competition: str | None = None,
) -> pd.Series | None:
    """Searchable select box over ``candidates``; remembers the choice across pages.

    Without a remembered player, the default is the outfield player with most minutes in
    ``prefer_competition`` (the focus league).
    """
    if candidates.empty:
        st.info(t("no_data", lang))
        return None
    focus = candidates["competition_id"].eq(prefer_competition) if prefer_competition else False
    outfield = candidates["position_group"].ne("Goalkeeper")
    ordered = candidates.assign(_focus=focus, _outfield=outfield).sort_values(
        ["_focus", "_outfield", "minutes"], ascending=False
    )
    keys = [player_key(r) for _, r in ordered.iterrows()]
    labels = {k: player_label(r) for k, (_, r) in zip(keys, ordered.iterrows(), strict=True)}
    remembered = st.session_state.get(SELECTED_KEY)
    index = keys.index(remembered) if remembered in labels else 0
    choice = st.selectbox(label, keys, index=index, format_func=labels.get)
    st.session_state[SELECTED_KEY] = choice
    return find_row(candidates, choice)


def next_contract_deadline(cutoff: pd.Timestamp) -> pd.Timestamp:
    """The next 30 June that is still open at the data cut-off.

    Contract dates are a snapshot. From May on, contracts ending this summer are already being
    settled (renewed or expired), so the next meaningful deadline is the following summer.
    """
    year = cutoff.year + (1 if cutoff.month >= 5 else 0)
    return pd.Timestamp(f"{year}-06-30")


def confidence_for_minutes(minutes: float, thresholds: tuple[int, int]) -> str:
    return confidence_from_sample(minutes, medium=thresholds[0], high=thresholds[1])


def money(value: float | None, lang: Lang) -> str:
    return format_money(value, lang)


def go_to(page: str, row: pd.Series | None = None) -> None:
    """Remember ``row`` (if given) and switch to one of :data:`PAGES`."""
    if row is not None:
        remember_player(row)
    st.switch_page(PAGES[page])
