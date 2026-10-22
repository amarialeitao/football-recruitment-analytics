"""Tests for percentiles. All values are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting.metrics.percentiles import PCT_SUFFIX, peer_group, percentile_ranks


def test_percentiles_compare_within_position_group_only(ps: pd.DataFrame) -> None:
    out = percentile_ranks(ps, ["goals_p90"], min_minutes=900)
    eligible = out[out["minutes"] >= 900]
    for name, group in eligible.groupby("position_group"):
        assert group["comparison_n"].iloc[0] == len(group)
        if name == "Goalkeeper":  # every keeper has 0 goals: all tie at the middle rank
            assert group["goals_p90_pct"].nunique() == 1
        else:
            assert group["goals_p90_pct"].max() == pytest.approx(100.0)


def test_lower_is_better_metrics_are_inverted(ps: pd.DataFrame) -> None:
    out = percentile_ranks(ps, ["goals_against_on_p90"], min_minutes=0)
    fwd = out[out["position_group"] == "Forward"]
    best = fwd.loc[fwd["goals_against_on_p90"].idxmin()]
    assert best["goals_against_on_p90" + PCT_SUFFIX] == pytest.approx(100.0)


def test_players_below_minimum_keep_row_without_percentile(ps: pd.DataFrame) -> None:
    out = percentile_ranks(ps, ["goals_p90"], min_minutes=900)
    below = out[out["minutes"] < 900]
    assert len(below) > 0
    assert below["goals_p90_pct"].isna().all()
    assert below["comparison_n"].isna().all()
    assert len(out) == len(ps)


def test_peer_group_filters(ps: pd.DataFrame) -> None:
    peers = peer_group(
        ps, position_group="Defender", season=2025, min_minutes=900, competitions=["AA1"]
    )
    assert set(peers["position_group"]) == {"Defender"}
    assert set(peers["competition_id"]) == {"AA1"}
    assert (peers["minutes"] >= 900).all()
