"""Value Finder: how a player's market value compares with what his output usually costs.

Method:

1. ``performance_score``: the mean of the player's profile percentiles (0-100), with optional
   weights. Percentiles must already be computed (see :mod:`scouting.metrics.percentiles`).
2. Expected value: a linear fit, within each position group, of ``log10(market value)`` on
   performance score, age, age squared and league strength (squad-value index). The fit uses only
   players above the minimum minutes with a known value.
3. ``value_ratio`` = actual value / expected value. Below 1 means the market values the player
   less than players with similar output, age and league: a candidate "undervalued" profile.

Values last updated more than ``STALE_DAYS`` before the season's end are marked
``market_value_stale``: they are left out of the fit and of :func:`undervalued` by default,
because an outdated value makes a player look cheap.

Market value is a crowd estimate, not a transfer fee; the page says so next to the chart.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from scouting.metrics.catalog import PROFILE_METRICS
from scouting.metrics.percentiles import PCT_SUFFIX

MIN_FIT_ROWS = 30
STALE_DAYS = 365


def performance_score(
    df: pd.DataFrame, weights: Mapping[str, Mapping[str, float]] | None = None
) -> pd.Series:
    """Weighted mean of each row's profile percentiles for its position group (0-100)."""
    score = pd.Series(np.nan, index=df.index, dtype="float64")
    for group, keys in PROFILE_METRICS.items():
        rows = df["position_group"] == group
        if not rows.any():
            continue
        group_weights = (weights or {}).get(group, {})
        w = np.array([float(group_weights.get(k, 1.0)) for k in keys])
        pct = df.loc[rows, [k + PCT_SUFFIX for k in keys]].to_numpy(dtype="float64")
        valid = ~np.isnan(pct)
        weighted = np.where(valid, pct, 0.0) @ w
        total = valid @ w
        with np.errstate(invalid="ignore", divide="ignore"):
            score.loc[rows] = np.where(total > 0, weighted / total, np.nan)
    return score


def _design(frame: pd.DataFrame) -> np.ndarray:
    age = frame["age"].to_numpy(dtype="float64")
    return np.column_stack(
        [
            np.ones(len(frame)),
            frame["performance_score"].to_numpy(dtype="float64"),
            age,
            age**2,
            np.log10(frame["strength_index"].to_numpy(dtype="float64")),
        ]
    )


def expected_value(
    df: pd.DataFrame,
    league_strength: pd.DataFrame,
    *,
    min_minutes: int,
    weights: Mapping[str, Mapping[str, float]] | None = None,
) -> pd.DataFrame:
    """Add ``performance_score``, ``strength_index``, ``expected_market_value``,
    ``value_ratio`` and ``fit_r2`` (per position group) to ``df``."""
    out = df.copy()
    out["performance_score"] = performance_score(out, weights)
    strength = league_strength[["competition_id", "season", "strength_index"]]
    out = out.merge(strength, on=["competition_id", "season"], how="left")
    out.index = df.index

    season_end = pd.to_datetime((out["season"] + 1).astype(str) + "-06-30")
    age_days = (season_end - pd.to_datetime(out["market_value_end_date"])).dt.days
    out["market_value_stale"] = age_days.isna() | (age_days > STALE_DAYS)

    out["expected_market_value"] = np.nan
    out["fit_r2"] = np.nan
    eligible = (
        (out["minutes"] >= min_minutes)
        & (out["market_value_end"] > 0)
        & ~out["market_value_stale"]
        & out[["performance_score", "age", "strength_index"]].notna().all(axis=1)
    )
    for group in PROFILE_METRICS:
        fit_rows = eligible & (out["position_group"] == group)
        if fit_rows.sum() < MIN_FIT_ROWS:
            continue
        x = _design(out[fit_rows])
        y = np.log10(out.loc[fit_rows, "market_value_end"].to_numpy(dtype="float64"))
        coef, *_ = np.linalg.lstsq(x, y, rcond=None)
        residual = y - x @ coef
        r2 = 1 - residual.var() / y.var() if y.var() > 0 else np.nan
        out.loc[fit_rows, "expected_market_value"] = 10 ** (x @ coef)
        out.loc[fit_rows, "fit_r2"] = r2

    out["value_ratio"] = out["market_value_end"] / out["expected_market_value"]
    return out


def undervalued(
    df: pd.DataFrame,
    *,
    max_market_value: float | None = None,
    max_ratio: float = 1.0,
    position_group: str | None = None,
    include_stale: bool = False,
) -> pd.DataFrame:
    """Rows with ``value_ratio`` at or below ``max_ratio``, cheapest-relative-to-output first."""
    mask = df["value_ratio"].notna() & (df["value_ratio"] <= max_ratio)
    if not include_stale:
        mask &= ~df["market_value_stale"]
    if max_market_value is not None:
        mask &= df["market_value_end"] <= max_market_value
    if position_group is not None:
        mask &= df["position_group"] == position_group
    return df[mask].sort_values("value_ratio")
