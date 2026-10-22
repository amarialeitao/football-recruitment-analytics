"""Percentile ranks of players against peers in the same position group.

A player is compared only with players of the same ``position_group`` who reached the minimum
minutes, within the pool the caller chooses (by default: all configured leagues, per season).
Percentiles run from 0 to 100, and "lower is better" metrics are inverted so 100 is always best.
Players below the minimum minutes keep their row, with empty percentiles.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd

from scouting.metrics.catalog import METRICS, metric

PCT_SUFFIX = "_pct"


def percentile_ranks(
    df: pd.DataFrame,
    metrics: Iterable[str] | None = None,
    *,
    min_minutes: int,
    group_by: Sequence[str] = ("season", "position_group"),
) -> pd.DataFrame:
    """Return ``df`` with one ``<metric>_pct`` column per metric and ``comparison_n``.

    ``comparison_n`` is the number of eligible players in the row's comparison group, i.e. the
    sample size behind each percentile.
    """
    keys = list(metrics) if metrics is not None else list(METRICS)
    out = df.copy()
    eligible = out["minutes"] >= min_minutes
    groups = list(group_by)

    pool = out[eligible]
    out["comparison_n"] = pool.groupby(groups)["player_id"].transform("size").astype("Int64")

    for key in keys:
        definition = metric(key)
        values = pool[key].astype("float64")
        if not definition.higher_is_better:
            values = -values
        # Average rank of ties, scaled so the best player is 100 and the worst is near 0.
        ranks = values.groupby([pool[c] for c in groups]).rank(method="average", pct=True)
        out[key + PCT_SUFFIX] = (ranks * 100).round(1).reindex(out.index)
    return out


def peer_group(
    df: pd.DataFrame,
    *,
    position_group: str,
    season: int,
    min_minutes: int,
    competitions: Iterable[str] | None = None,
) -> pd.DataFrame:
    """The eligible players a percentile is computed against (for 'compared with whom?' notes)."""
    mask = (
        (df["position_group"] == position_group)
        & (df["season"] == season)
        & (df["minutes"] >= min_minutes)
    )
    if competitions is not None:
        mask &= df["competition_id"].isin(list(competitions))
    return df[mask]
