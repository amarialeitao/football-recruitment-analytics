"""The shortlist: players a scout wants to keep an eye on, collected from any page.

Kept in ``st.session_state`` as an ordered list of ``(player_id, season, competition_id)`` keys,
so it survives moving between pages for as long as the app is open. It is not saved anywhere
else: the Shortlist page exports it as CSV to keep or share.
"""

from __future__ import annotations

from collections.abc import MutableMapping

import pandas as pd
import streamlit as st

from scouting.ui.i18n import Lang
from scouting.ui.players import player_key

STATE_KEY = "shortlist"
MAX_PLAYERS = 30
MAX_COMPARE = 3

TEXT = {
    "add": {"en": "Add to shortlist", "pt": "Adicionar à lista"},
    "remove": {"en": "Remove from shortlist", "pt": "Retirar da lista"},
    "full": {
        "en": "The shortlist is full ({n} players). Remove someone first.",
        "pt": "A lista está cheia ({n} jogadores). Retire alguém primeiro.",
    },
}

Key = tuple[int, int, str]


def keys(state: MutableMapping | None = None) -> list[Key]:
    state = st.session_state if state is None else state
    return list(state.get(STATE_KEY, []))


def contains(key: Key, state: MutableMapping | None = None) -> bool:
    return key in keys(state)


def add(key: Key, state: MutableMapping | None = None) -> bool:
    """Add ``key`` at the end. False if it was already there or the list is full."""
    state = st.session_state if state is None else state
    current = keys(state)
    if key in current or len(current) >= MAX_PLAYERS:
        return False
    state[STATE_KEY] = [*current, key]
    return True


def remove(key: Key, state: MutableMapping | None = None) -> None:
    state = st.session_state if state is None else state
    state[STATE_KEY] = [k for k in keys(state) if k != key]


def clear(state: MutableMapping | None = None) -> None:
    state = st.session_state if state is None else state
    state[STATE_KEY] = []


def rows(players: pd.DataFrame, state: MutableMapping | None = None) -> pd.DataFrame:
    """The shortlisted rows of ``players``, in the order they were added."""
    wanted = keys(state)
    if not wanted:
        return players.iloc[0:0]
    index = pd.MultiIndex.from_frame(
        players[["player_id", "season", "competition_id"]].astype(
            {"player_id": "int64", "season": "int64", "competition_id": "str"}
        )
    )
    position = {k: i for i, k in enumerate(wanted)}
    order = [position.get(tuple(k)) for k in index]
    found = players.assign(_order=order).dropna(subset=["_order"])
    return found.sort_values("_order").drop(columns="_order")


def toggle_button(row: pd.Series, lang: Lang, *, key: str, container=None) -> None:
    """'Add to shortlist' or 'Remove from shortlist' for ``row``."""
    target = st if container is None else container
    k = player_key(row)
    if contains(k):
        if target.button(TEXT["remove"][lang], key=key, icon=":material/bookmark_remove:"):
            remove(k)
            st.rerun()
    elif target.button(TEXT["add"][lang], key=key, icon=":material/bookmark_add:"):
        if not add(k):
            st.warning(TEXT["full"][lang].format(n=MAX_PLAYERS))
        else:
            st.rerun()
