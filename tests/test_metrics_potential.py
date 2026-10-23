"""Tests for potential. All values are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from metric_data import synthetic_player_season
from scouting.metrics.potential import potential_signals


def test_potential_returns_only_young_players_with_signals(ps: pd.DataFrame) -> None:
    out = potential_signals(ps, young_age_max=23)
    assert (out["age"] <= 23).all()
    assert out["signals_met"].between(0, 3).all()
    assert out["signals_met"].is_monotonic_decreasing


def test_potential_value_growth_and_small_bands() -> None:
    df = synthetic_player_season(n_per_group=4)
    df["age"] = 20.5
    df.loc[0, ["market_value_start", "market_value_end"]] = [1e6, 2e6]
    out = potential_signals(df, young_age_max=23).set_index("player_id")
    assert out.loc[1, "value_growth"] == pytest.approx(1.0)
    # Bands with fewer than 5 peers get no percentile rather than a misleading one.
    assert out["minutes_for_age_pct"].isna().all()


def test_potential_compares_with_regulars_only() -> None:
    df = synthetic_player_season(n_per_group=40)
    df["age"] = 21.0
    out = potential_signals(df, young_age_max=23, min_minutes=900)
    regulars = out[out["minutes"] >= 900]
    below = out[out["minutes"] < 900]
    assert regulars["minutes_for_age_pct"].notna().all()
    assert below["minutes_for_age_pct"].isna().all()
    assert (
        regulars["age_band_n"] == regulars.groupby("position_group")["player_id"].transform("size")
    ).all()
