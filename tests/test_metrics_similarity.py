"""Tests for similarity. All values are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting.metrics.similarity import find_similar


def _ref(ps: pd.DataFrame, group: str = "Forward") -> dict:
    row = ps[(ps["position_group"] == group) & (ps["minutes"] >= 900)].iloc[0]
    return {
        "player_id": row["player_id"],
        "season": row["season"],
        "competition_id": row["competition_id"],
    }


def test_similar_players_share_position_and_exclude_reference(ps: pd.DataFrame) -> None:
    ref = _ref(ps)
    out = find_similar(ps, ref, min_minutes=900, top_n=5)
    assert len(out) == 5
    assert set(out["position_group"]) == {"Forward"}
    assert ref["player_id"] not in out["player_id"].tolist()
    assert out["similarity"].is_monotonic_decreasing
    assert out["similarity"].between(0, 100).all()


def test_identical_profile_scores_100(ps: pd.DataFrame) -> None:
    ref = _ref(ps)
    clone = ps[ps["player_id"] == ref["player_id"]].copy()
    clone["player_id"] = 9999
    out = find_similar(pd.concat([ps, clone], ignore_index=True), ref, min_minutes=900, top_n=1)
    assert out.loc[0, "player_id"] == 9999
    assert out.loc[0, "similarity"] == pytest.approx(100.0)


def test_similarity_filters_apply_to_candidates(ps: pd.DataFrame) -> None:
    out = find_similar(
        ps, _ref(ps), min_minutes=900, competitions=["BB1"], max_age=25, max_market_value=5e6
    )
    assert set(out["competition_id"]) <= {"BB1"}
    assert (out["age"] <= 25).all()
    assert (out["market_value_end"] <= 5e6).all()


def test_similarity_unknown_reference(ps: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="not found"):
        find_similar(ps, {"player_id": -1, "season": 2025, "competition_id": "AA1"}, min_minutes=0)
