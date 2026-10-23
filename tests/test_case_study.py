"""Case study rules on synthetic data. All names and numbers are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting.case_study import Brief, pick_alternatives, shortlist
from scouting.metrics.percentiles import percentile_ranks
from scouting.metrics.value import expected_value


@pytest.fixture
def players(ps: pd.DataFrame) -> pd.DataFrame:
    strength = pd.DataFrame(
        {"competition_id": ["AA1", "BB1"], "season": [2025, 2025], "strength_index": [100.0, 60.0]}
    )
    out = expected_value(percentile_ranks(ps, min_minutes=900), strength, min_minutes=900)
    defenders = out["position_group"] == "Defender"
    out["sub_position"] = "Other"
    out.loc[defenders, "sub_position"] = ["Right-Back", "Centre-Back"] * (defenders.sum() // 2)
    out["name"] = "P" + out["player_id"].astype(str)
    return out


def _brief(players: pd.DataFrame, **overrides) -> Brief:
    rb = players[(players["sub_position"] == "Right-Back") & (players["minutes"] >= 900)]
    ref = rb.sort_values("minutes").iloc[-1]
    params = {
        "reference": {k: ref[k] for k in ("player_id", "season", "competition_id")},
        "positions": ["Right-Back"],
        "max_market_value": 8e6,
        "max_age": 30,
        "min_minutes": 1000,
        "exclude_club_ids": [int(ref["club_id"])],
    }
    params.update(overrides)
    return Brief(**params)


def test_shortlist_applies_every_criterion(players: pd.DataFrame) -> None:
    brief = _brief(players)
    out = shortlist(players, brief, comparison_min_minutes=900)
    assert len(out) > 0
    assert set(out["sub_position"]) == {"Right-Back"}
    assert (out["minutes"] >= 1000).all()
    assert (out["age"] <= 30).all()
    assert (out["market_value_end"] <= 8e6).all()
    assert not out["club_id"].isin(brief.exclude_club_ids).any()
    assert brief.reference["player_id"] not in out["player_id"].tolist()
    assert out["similarity"].is_monotonic_decreasing


def test_shortlist_drops_stale_values(players: pd.DataFrame) -> None:
    brief = _brief(players)
    first = shortlist(players, brief, comparison_min_minutes=900).iloc[0]["player_id"]
    players.loc[players["player_id"] == first, "market_value_stale"] = True
    assert first not in shortlist(players, brief, comparison_min_minutes=900)["player_id"].tolist()


def test_picks_are_distinct_and_follow_rules(players: pd.DataFrame) -> None:
    brief = _brief(players, top_similar=12, min_minutes_share=0.0)
    candidates = shortlist(players, brief, comparison_min_minutes=900)
    picks = pick_alternatives(candidates, brief)
    assert picks["pick"].tolist()[0] == "closest_profile"
    assert picks.iloc[0]["player_id"] == candidates.iloc[0]["player_id"]
    assert picks["player_id"].is_unique

    top = candidates.head(brief.top_similar)
    if "best_value" in picks["pick"].tolist():
        best = picks.set_index("pick").loc["best_value"]
        floor = candidates["performance_score"].quantile(brief.value_floor_quantile)
        assert best["performance_score"] >= floor
        eligible = top[(top["performance_score"] >= floor) & (top.index != 0)]
        assert best["value_ratio"] == eligible["value_ratio"].min()
    if "younger_upside" in picks["pick"].tolist():
        young = picks.set_index("pick").loc["younger_upside"]
        floor = candidates["performance_score"].quantile(brief.young_floor_quantile)
        assert young["performance_score"] >= floor


def test_value_floor_blocks_cheap_low_output_players(players: pd.DataFrame) -> None:
    brief = _brief(players, top_similar=50)
    candidates = shortlist(players, brief, comparison_min_minutes=900)
    # Make the weakest candidate absurdly cheap relative to expectations.
    weakest = candidates["performance_score"].idxmin()
    candidates.loc[weakest, "value_ratio"] = 0.01
    picks = pick_alternatives(candidates, brief)
    assert candidates.loc[weakest, "player_id"] not in picks["player_id"].tolist()


def test_empty_shortlist(players: pd.DataFrame) -> None:
    brief = _brief(players, max_market_value=1.0)
    candidates = shortlist(players, brief, comparison_min_minutes=900)
    assert candidates.empty
    assert pick_alternatives(candidates, brief).empty
