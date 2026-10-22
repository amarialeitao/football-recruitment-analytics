"""Potential signals for young players. Signals, not predictions.

Three observable signals, each compared with players of the same position group and age band:

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


def potential_signals(df: pd.DataFrame, *, young_age_max: float) -> pd.DataFrame:
    """Return young players (``age <= young_age_max``) with their potential signals.

    Age bands are compared against *all* players of that age with minutes, not only the
    young subset, so the comparison group is as large as possible.
    """
    out = df.dropna(subset=["age", "position_group"]).copy()
    out["age_band"] = np.floor(out["age"]).astype("int64")
    groups = ["season", "position_group", "age_band"]
    out["age_band_n"] = out.groupby(groups)["player_id"].transform("size")
    out["minutes_for_age_pct"] = _pct_within(out, "minutes_share", groups)
    out["start_rate_for_age_pct"] = _pct_within(out, "start_rate", groups)

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
