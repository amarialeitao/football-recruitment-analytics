"""Shortlist: state helpers, comparison chart and the page with players in it. Invented data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scouting.app_data import build_app_data
from scouting.config import load_settings
from scouting.metrics.catalog import PROFILE_METRICS
from scouting.metrics.percentiles import percentile_ranks
from scouting.ui import charts
from scouting.ui import shortlist as sl
from test_pages import ROOT, app_env  # noqa: F401  (fixture)


def _players() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_id": [1, 2, 3],
            "season": [2025, 2025, 2024],
            "competition_id": ["AA1", "AA1", "BB1"],
            "name": ["A", "B", "C"],
        }
    )


def test_add_keeps_order_and_ignores_duplicates() -> None:
    state: dict = {}
    assert sl.add((2, 2025, "AA1"), state)
    assert sl.add((1, 2025, "AA1"), state)
    assert not sl.add((2, 2025, "AA1"), state)
    assert sl.keys(state) == [(2, 2025, "AA1"), (1, 2025, "AA1")]
    assert list(sl.rows(_players(), state)["name"]) == ["B", "A"]


def test_remove_clear_and_unknown_keys() -> None:
    state: dict = {}
    for key in [(1, 2025, "AA1"), (3, 2024, "BB1"), (9, 2025, "ZZ1")]:
        sl.add(key, state)
    sl.remove((1, 2025, "AA1"), state)
    assert list(sl.rows(_players(), state)["name"]) == ["C"]  # (9, ...) is not in the data
    sl.clear(state)
    assert sl.keys(state) == []
    assert sl.rows(_players(), state).empty


def test_list_has_a_limit() -> None:
    state: dict = {}
    for i in range(sl.MAX_PLAYERS):
        assert sl.add((i, 2025, "AA1"), state)
    assert not sl.add((999, 2025, "AA1"), state)
    assert len(sl.keys(state)) == sl.MAX_PLAYERS


def test_compare_chart_one_series_per_player(ps: pd.DataFrame) -> None:
    ranked = percentile_ranks(ps, min_minutes=0)
    forwards = ranked[ranked["position_group"] == "Forward"].head(3)
    keys = list(PROFILE_METRICS["Forward"])
    fig = charts.percentile_compare(
        [r for _, r in forwards.iterrows()], ["A", "B", "C"], keys, "en", title="T"
    )
    # Added in reverse so the first player is drawn on top; the legend is reversed to match.
    assert [tr.name for tr in fig.data] == ["C", "B", "A"]
    assert [tr.marker.color for tr in fig.data] == list(charts.COMPARE_COLORS)[::-1]
    assert fig.layout.legend.traceorder == "reversed"
    assert all(len(tr.x) == len(keys) for tr in fig.data)


def _top(config: Path, n: int) -> pd.DataFrame:
    data = build_app_data(load_settings(config), today=pd.Timestamp("2026-10-23"))
    return data.players.sort_values("minutes", ascending=False).head(n)


def _shortlisted_keys(config: Path, n: int) -> list[tuple[int, int, str]]:
    top = _top(config, n)
    return [(int(r.player_id), int(r.season), str(r.competition_id)) for r in top.itertuples()]


@pytest.mark.parametrize("lang", ["en", "pt"])
def test_page_with_players(app_env: Path, lang: str) -> None:  # noqa: F811
    keys = _shortlisted_keys(app_env, 3)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["lang"] = lang
    at.session_state["shortlist"] = keys
    at.run()
    at.switch_page("pages/7_Shortlist.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.dataframe) >= 2  # the list and the side-by-side table
    assert len(at.dataframe[0].value) == len(keys)
    # With nothing selected, the comparison shows the players from the same position group as
    # the first one added (percentiles are only comparable within a group).
    top = _top(app_env, 3)
    same_group = (top["position_group"] == top.iloc[0]["position_group"]).sum()
    side_by_side = at.dataframe[-1].value
    assert side_by_side.shape[1] == 1 + min(int(same_group), sl.MAX_COMPARE)
    assert list(side_by_side.columns[1:2]) == [str(top.iloc[0]["name"])]


def test_navigation_shows_the_count(app_env: Path) -> None:  # noqa: F811
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["shortlist"] = _shortlisted_keys(app_env, 2)
    at.run()
    assert not at.exception
    clear = [b for b in at.button if b.label == "Clear shortlist"]
    assert not clear  # not on the overview page
    at.switch_page("pages/7_Shortlist.py")
    at.run()
    [b for b in at.button if b.label == "Clear shortlist"][0].click().run()
    assert at.session_state["shortlist"] == []
