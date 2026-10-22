"""Tests for value. All values are invented."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scouting.metrics import catalog
from scouting.metrics.percentiles import PCT_SUFFIX, percentile_ranks
from scouting.metrics.value import expected_value, performance_score, undervalued


@pytest.fixture
def strength() -> pd.DataFrame:
    return pd.DataFrame(
        {"competition_id": ["AA1", "BB1"], "season": [2025, 2025], "strength_index": [100.0, 70.0]}
    )


def test_performance_score_is_weighted_mean_of_profile_percentiles(ps: pd.DataFrame) -> None:
    pct = percentile_ranks(ps, min_minutes=900)
    score = performance_score(pct)
    row = pct[(pct["position_group"] == "Goalkeeper") & pct["minutes"].ge(900)].iloc[0]
    keys = catalog.PROFILE_METRICS["Goalkeeper"]
    assert score[row.name] == pytest.approx(np.mean([row[k + PCT_SUFFIX] for k in keys]))
    only_first = {"Goalkeeper": {k: (1.0 if k == keys[0] else 0.0) for k in keys}}
    assert performance_score(pct, only_first)[row.name] == pytest.approx(row[keys[0] + PCT_SUFFIX])


def test_expected_value_fits_and_flags(ps: pd.DataFrame, strength: pd.DataFrame) -> None:
    out = expected_value(percentile_ranks(ps, min_minutes=900), strength, min_minutes=900)
    fitted = out[out["expected_market_value"].notna()]
    assert len(fitted) > 0
    assert (fitted["minutes"] >= 900).all()
    assert fitted["fit_r2"].between(0, 1).all()
    assert out["value_ratio"].dropna().gt(0).all()
    assert len(out) == len(ps)


def test_stale_values_are_excluded(ps: pd.DataFrame, strength: pd.DataFrame) -> None:
    ps.loc[0, "market_value_end_date"] = pd.Timestamp("2023-01-01")
    out = expected_value(percentile_ranks(ps, min_minutes=0), strength, min_minutes=0)
    assert bool(out.loc[0, "market_value_stale"])
    assert pd.isna(out.loc[0, "expected_market_value"])
    assert 1 not in undervalued(out, max_ratio=10)["player_id"].tolist()


def test_undervalued_filters_and_order(ps: pd.DataFrame, strength: pd.DataFrame) -> None:
    out = expected_value(percentile_ranks(ps, min_minutes=900), strength, min_minutes=900)
    cheap = undervalued(out, max_market_value=4e6, position_group="Defender")
    assert (cheap["value_ratio"] <= 1).all()
    assert (cheap["market_value_end"] <= 4e6).all()
    assert set(cheap["position_group"]) <= {"Defender"}
    assert cheap["value_ratio"].is_monotonic_increasing
