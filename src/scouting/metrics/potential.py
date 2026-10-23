"""Potential signals for young players. Signals, not predictions.

Three observable signals. The first two compare a player with *regulars* (players above the
minimum minutes) of the same position group and age band in the same season, so the signal says
"plays more than other young regulars", not just "plays":

* ``minutes_for_age_pct``: share of team minutes vs peers of the same age (rounded down) and
  position group in the same season. Playing a lot young is the most robust public signal.
* ``start_rate_for_age_pct``: the same comparison for the start rate.
* ``value_growth``: relative change in market value over the season (start -> end).

``signals_met`` counts how many of these are strong (percentile >= 75, growth >= 25%).
The data covers only the configured seasons, so career history before them is not included.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STRONG_PERCENTILE = 75.0
STRONG_VALUE_GROWTH = 0.25
MIN_PEERS = 5


def _pct_within(df: pd.DataFrame, column: str, groups: list[str]) -> pd.Series:
    ranks = df.groupby(groups)[column].rank(method="average", pct=True) * 100
    sizes = df.groupby(groups)[column].transform("count")
    return ranks.where(sizes >= MIN_PEERS).round(1)


def potential_signals(
    df: pd.DataFrame, *, young_age_max: float, min_minutes: int = 0
) -> pd.DataFrame:
    """Return young players (``age <= young_age_max``) with their potential signals.

    Percentiles are computed among players of the same season, position group and age band
    who reached ``min_minutes``. Players below it keep their row with empty percentiles.
    """
    out = df.dropna(subset=["age", "position_group"]).copy()
    out["age_band"] = np.floor(out["age"]).astype("int64")
    groups = ["season", "position_group", "age_band"]
    pool = out[out["minutes"] >= min_minutes]
    out["age_band_n"] = pool.groupby(groups)["player_id"].transform("size").reindex(out.index)
    out["minutes_for_age_pct"] = _pct_within(pool, "minutes_share", groups).reindex(out.index)
    out["start_rate_for_age_pct"] = _pct_within(pool, "start_rate", groups).reindex(out.index)

    start = out["market_value_start"].astype("float64")
    end = out["market_value_end"].astype("float64")
    out["value_growth"] = (end - start) / start.where(start > 0)

    out["signals_met"] = (
        (out["minutes_for_age_pct"] >= STRONG_PERCENTILE).astype(int)
        + (out["start_rate_for_age_pct"] >= STRONG_PERCENTILE).astype(int)
        + (out["value_growth"] >= STRONG_VALUE_GROWTH).astype(int)
    )
    young = out[out["age"] <= young_age_max]
    return young.sort_values(
        ["signals_met", "minutes_for_age_pct", "value_growth"], ascending=False
    )
