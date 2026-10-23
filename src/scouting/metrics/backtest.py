"""Backtest of the value model: did players it rated cheap for their output gain value later?

The question a sporting director would ask about the Value Finder is "has this ever worked?".
The test answers it with data the model could not have seen:

1. **Fit on one season only.** The value model is fitted on the base season alone (for
   example 2023/24), exactly as a scout would have seen it at the end of that season.
2. **Look forward.** For each player, the market value at the end of the base season is
   compared with his latest value ``horizon_years`` later. Players with no valuation update
   after the base season cannot be followed and are counted separately.
3. **Compare fairly.** Cheaper players and younger players tend to lose less value anyway, so a
   raw comparison flatters the model. Three views are reported:

   * **quintiles** of value vs expected (raw pattern);
   * **like-for-like**: flagged players against unflagged players of the same position, age band
     and price band;
   * **regression** of value change on log value vs expected, holding current value, age,
     position and league strength constant.

Market value is itself a crowd estimate, so the test asks whether the crowd later caught up
with what the model saw, not whether the players became better.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from scouting.metrics.value import expected_value

AGE_BANDS = [0, 21, 23, 25, 27, 29, 60]
PRICE_BANDS = 8  # quantile bands of current market value
POSITIONS = ("Defender", "Forward", "Midfielder")  # goalkeeper is the baseline in the regression


@dataclass(frozen=True)
class BacktestResult:
    base_season: int
    horizon_years: int
    flag_ratio: float
    players: pd.DataFrame  # one row per followed player, with value_ratio, growth, flagged
    n_rated: int  # players the model rated in the base season
    followed_share_flagged: float
    followed_share_others: float
    quintiles: pd.DataFrame
    flagged_vs_others: pd.DataFrame
    matched_value_change: float  # flagged / like-for-like others, median multiplier
    matched_rose_diff: float  # difference in share whose value rose, percentage points
    matched_n: int
    regression_coef: float  # change in log10 growth per unit of log10(value vs expected)
    regression_se: float  # heteroskedasticity-robust (HC1) standard error

    @property
    def half_price_effect(self) -> float:
        """Value change multiplier for a player rated at half his expected value."""
        return 10 ** (self.regression_coef * np.log10(0.5))


def value_at(valuations: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """Latest market value per player on or before ``day`` (columns: date, value)."""
    v = valuations[pd.to_datetime(valuations["date"]) <= day].sort_values("date")
    latest = v.groupby("player_id").last()
    return latest.rename(columns={"market_value_in_eur": "value"})[["date", "value"]]


def _ols_robust(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and HC1 robust standard errors (``x`` includes the constant)."""
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ beta
    n, k = x.shape
    inv = np.linalg.pinv(x.T @ x)
    meat = (x * residual[:, None]).T @ (x * residual[:, None])
    cov = inv @ meat @ inv * n / max(n - k, 1)
    return beta, np.sqrt(np.diag(cov))


def run_backtest(
    ranked: pd.DataFrame,
    league_strength: pd.DataFrame,
    valuations: pd.DataFrame,
    *,
    base_season: int,
    horizon_years: int,
    min_minutes: int,
    flag_ratio: float = 0.5,
) -> BacktestResult:
    """Run the backtest. ``ranked`` is the player-season table with percentiles."""
    rated = expected_value(
        ranked[ranked["season"] == base_season], league_strength, min_minutes=min_minutes
    )
    rated = rated[rated["value_ratio"].notna()].copy()
    rated["flagged"] = rated["value_ratio"] <= flag_ratio

    start = pd.Timestamp(f"{base_season + 1}-06-30")
    later = value_at(valuations, start + pd.DateOffset(years=horizon_years))
    merged = rated.merge(later, left_on="player_id", right_index=True, how="left")
    followed = merged["date"].notna() & (pd.to_datetime(merged["date"]) > start)

    def share(mask: pd.Series) -> float:
        return float(followed[mask].mean()) if mask.any() else float("nan")

    followed_flagged = share(merged["flagged"])
    followed_others = share(~merged["flagged"])

    out = merged[followed].copy()
    out["growth"] = np.log10(out["value"] / out["market_value_end"])
    out["rose"] = out["growth"] > 0

    def summary(frame: pd.DataFrame) -> pd.Series:
        return pd.Series(
            {
                "players": len(frame),
                "median_value_ratio": frame["value_ratio"].median(),
                "median_value_change": 10 ** frame["growth"].median(),
                "share_rose": frame["rose"].mean(),
            }
        )

    out["quintile"] = pd.qcut(out["value_ratio"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    quintiles = out.groupby("quintile").apply(summary, include_groups=False)
    flagged_vs_others = (
        out.assign(group=np.where(out["flagged"], "flagged", "others"))
        .groupby("group")
        .apply(summary, include_groups=False)
    )

    # Like-for-like: same position group, age band and price band.
    out["age_band"] = pd.cut(out["age"], AGE_BANDS)
    out["price_band"] = pd.qcut(np.log10(out["market_value_end"]), PRICE_BANDS, duplicates="drop")
    weights, growth_diff, rose_diff = [], [], []
    for _, cell in out.groupby(["position_group", "age_band", "price_band"], observed=True):
        flagged, others = cell[cell["flagged"]], cell[~cell["flagged"]]
        if flagged.empty or others.empty:
            continue
        weights.append(len(flagged))
        growth_diff.append(flagged["growth"].median() - others["growth"].median())
        rose_diff.append(flagged["rose"].mean() - others["rose"].mean())
    w = np.asarray(weights, dtype="float64")
    matched_change = float(10 ** (np.dot(w, growth_diff) / w.sum())) if w.size else float("nan")
    matched_rose = float(100 * np.dot(w, rose_diff) / w.sum()) if w.size else float("nan")

    # Regression with controls.
    age = out["age"].to_numpy(dtype="float64")
    columns = [
        np.ones(len(out)),
        np.log10(out["value_ratio"].to_numpy(dtype="float64")),
        np.log10(out["market_value_end"].to_numpy(dtype="float64")),
        age,
        age**2,
        np.log10(out["strength_index"].to_numpy(dtype="float64")),
        *[(out["position_group"] == p).to_numpy(dtype="float64") for p in POSITIONS],
    ]
    beta, se = _ols_robust(out["growth"].to_numpy(dtype="float64"), np.column_stack(columns))

    keep = [
        "player_id",
        "name",
        "position_group",
        "competition_id",
        "age",
        "market_value_end",
        "value_ratio",
        "flagged",
        "value",
        "growth",
        "rose",
    ]
    return BacktestResult(
        base_season=base_season,
        horizon_years=horizon_years,
        flag_ratio=flag_ratio,
        players=out[[c for c in keep if c in out.columns]].reset_index(drop=True),
        n_rated=len(rated),
        followed_share_flagged=followed_flagged,
        followed_share_others=followed_others,
        quintiles=quintiles,
        flagged_vs_others=flagged_vs_others,
        matched_value_change=matched_change,
        matched_rose_diff=matched_rose,
        matched_n=int(w.sum()),
        regression_coef=float(beta[1]),
        regression_se=float(se[1]),
    )
