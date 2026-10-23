"""Backtest of the value model on synthetic worlds where the right answer is known."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from metric_data import synthetic_player_season
from scouting.metrics.backtest import run_backtest, value_at
from scouting.metrics.percentiles import percentile_ranks

STRENGTH = pd.DataFrame(
    {"competition_id": ["AA1", "BB1"], "season": [2025, 2025], "strength_index": [100.0, 70.0]}
)
START = pd.Timestamp("2026-06-30")  # end of the 2025/26 base season


@pytest.fixture
def ranked() -> pd.DataFrame:
    ps = synthetic_player_season(n_per_group=150, seed=3)
    noise = np.random.default_rng(11).lognormal(0, 0.5, len(ps))
    ps["market_value_end"] = ps["market_value_end"] * noise  # some players priced off their output
    return percentile_ranks(ps, min_minutes=900)


def _later(ranked: pd.DataFrame, catch_up: float, *, drop_every: int = 0, seed: int = 5):
    """Valuations: one at the base date, one six months later.

    ``catch_up`` = how strongly a cheap-for-output price moves back towards the model (0 = not at
    all, only noise). Every ``drop_every``-th player gets no later update.
    """
    from scouting.metrics.value import expected_value

    fitted = expected_value(ranked, STRENGTH, min_minutes=900)
    ratio = fitted["value_ratio"].fillna(1.0).to_numpy()
    rng = np.random.default_rng(seed)
    later = (
        fitted["market_value_end"].to_numpy()
        * ratio ** (-catch_up)
        * rng.lognormal(0, 0.1, len(ratio))
    )
    rows = [
        {"player_id": pid, "date": START - pd.Timedelta(days=60), "market_value_in_eur": v}
        for pid, v in zip(fitted["player_id"], fitted["market_value_end"], strict=True)
    ]
    for i, (pid, v) in enumerate(zip(fitted["player_id"], later, strict=True)):
        if drop_every and i % drop_every == 0:
            continue
        rows.append(
            {"player_id": pid, "date": START + pd.Timedelta(days=180), "market_value_in_eur": v}
        )
    return pd.DataFrame(rows)


def _run(ranked: pd.DataFrame, valuations: pd.DataFrame):
    return run_backtest(
        ranked, STRENGTH, valuations, base_season=2025, horizon_years=1, min_minutes=900
    )


def test_value_at_takes_latest_on_or_before_day() -> None:
    v = pd.DataFrame(
        {
            "player_id": [1, 1, 1, 2],
            "date": pd.to_datetime(["2024-01-01", "2025-01-01", "2026-01-01", "2026-01-01"]),
            "market_value_in_eur": [1.0, 2.0, 3.0, 9.0],
        }
    )
    out = value_at(v, pd.Timestamp("2025-06-30"))
    assert out.loc[1, "value"] == 2.0
    assert 2 not in out.index


def test_detects_a_market_that_catches_up(ranked: pd.DataFrame) -> None:
    result = _run(ranked, _later(ranked, catch_up=0.5))
    assert result.regression_coef < -0.3  # cheaper for output -> bigger rise
    assert abs(result.regression_coef / result.regression_se) > 5
    assert result.half_price_effect > 1.2
    q = result.quintiles["median_value_change"]
    assert q.loc[1] > q.loc[5]
    assert result.matched_value_change > 1.0
    assert (
        result.flagged_vs_others.loc["flagged", "share_rose"]
        > (result.flagged_vs_others.loc["others", "share_rose"])
    )


def test_finds_nothing_when_there_is_nothing(ranked: pd.DataFrame) -> None:
    result = _run(ranked, _later(ranked, catch_up=0.0))
    assert abs(result.regression_coef) < 3 * result.regression_se
    assert result.half_price_effect == pytest.approx(1.0, abs=0.05)


def test_unfollowed_players_are_counted_not_guessed(ranked: pd.DataFrame) -> None:
    result = _run(ranked, _later(ranked, catch_up=0.5, drop_every=4))
    assert len(result.players) < result.n_rated
    assert 0.6 < result.followed_share_others <= 0.8
    assert result.players["growth"].notna().all()
    assert set(result.quintiles.index) == {1, 2, 3, 4, 5}
    assert result.quintiles["players"].sum() == len(result.players)
