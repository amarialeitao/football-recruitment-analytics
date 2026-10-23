"""Find players with a profile similar to a reference player.

Method (kept simple so it can be explained to a sporting director):

1. Candidates: same position group and season scope as the reference, minimum minutes reached.
2. Features: the position group's profile metrics (per 90 and usage), each standardized to a
   z-score within the candidate pool, with "lower is better" metrics flipped. Optional weights
   change how much each feature counts.
3. Similarity: ``100 * exp(-d / sqrt(k))``, where ``d`` is the Euclidean distance between the
   reference and the candidate in z-score units and ``k`` the number of features. An identical
   profile scores 100; a typical pair of players scores around 30. Distance (not cosine)
   is used so that intensity counts: a player with half the output in every metric is not
   "identical".

The result says *who plays a similar statistical role with the data available*, not who is as
good: the public data has no passing, defending or shot-quality metrics.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

from scouting.metrics.catalog import PROFILE_METRICS, metric

KEY = ["player_id", "season", "competition_id"]


def _standardize(pool: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    z = pd.DataFrame(index=pool.index)
    for key in features:
        values = pool[key].astype("float64")
        std = values.std(ddof=0)
        scaled = (values - values.mean()) / std if std and np.isfinite(std) else values * 0.0
        z[key] = scaled if metric(key).higher_is_better else -scaled
    return z.fillna(0.0)


def find_similar(
    df: pd.DataFrame,
    reference: Mapping[str, object],
    *,
    min_minutes: int,
    features: Iterable[str] | None = None,
    weights: Mapping[str, float] | None = None,
    seasons: Iterable[int] | None = None,
    competitions: Iterable[str] | None = None,
    max_age: float | None = None,
    max_market_value: float | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Return the ``top_n`` most similar player-seasons to ``reference``.

    ``reference`` identifies one row by ``player_id``, ``season`` and ``competition_id``.
    Filters (seasons, competitions, age, market value) restrict the candidates returned, not the
    pool used for standardization, so scores stay comparable when filters change.
    """
    mask = np.ones(len(df), dtype=bool)
    for column in KEY:
        mask &= (df[column] == reference[column]).to_numpy()
    if mask.sum() != 1:
        raise ValueError(f"Reference player-season not found (or not unique): {dict(reference)}")
    ref_row = df[mask].iloc[0]
    group = ref_row["position_group"]
    keys = list(features) if features is not None else list(PROFILE_METRICS[group])

    pool = df[(df["position_group"] == group) & (df["minutes"] >= min_minutes)]
    if not mask[df.index.get_indexer(pool.index)].any():
        pool = pd.concat([pool, df[mask]])  # keep the reference even below the minimum

    z = _standardize(pool, keys)
    w = np.array([float((weights or {}).get(k, 1.0)) for k in keys])
    vectors = z.to_numpy() * w
    ref_vector = vectors[pool.index.get_loc(ref_row.name)]

    distance = np.linalg.norm(vectors - ref_vector, axis=1)

    result = pool.copy()
    result["similarity"] = np.round(100 * np.exp(-distance / np.sqrt(len(keys))), 1)
    result["distance"] = distance

    is_reference = result["player_id"] == ref_row["player_id"]
    result = result[~is_reference]
    if seasons is not None:
        result = result[result["season"].isin(list(seasons))]
    if competitions is not None:
        result = result[result["competition_id"].isin(list(competitions))]
    if max_age is not None:
        result = result[result["age"] <= max_age]
    if max_market_value is not None:
        result = result[result["market_value_end"] <= max_market_value]

    ordered = result.sort_values(["distance", "player_id"])
    return ordered.head(top_n).reset_index(drop=True)
