"""Recruitment case study: replace a key player with a low-cost alternative.

The method is deliberately rule-based so every step can be explained and reproduced:

1. **Brief**: the player to replace, the positions that can replace him, a market-value cap
   (the budget), an age cap and a minimum of minutes (high-confidence sample).
2. **Shortlist**: players of the same season in the leagues in scope who meet the brief,
   ranked by similarity to the reference profile (:func:`scouting.metrics.similarity`).
3. **Three alternatives**, each answering a different question:

   * ``closest_profile``: the most similar profile within budget;
   * ``best_value``: among the most similar candidates with strong output (performance score in
     the shortlist's top quarter), the one valued furthest below what his output usually costs
     (lowest ``value_ratio``). The output floor stops "cheap because he produces little" picks;
   * ``younger_upside``: among the most similar candidates performing at least at the shortlist
     median, the youngest who already plays most of his team's minutes.

Market value is a crowd estimate, not a fee; the shortlist is a starting point for scouting,
not a decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd

from scouting.metrics.similarity import find_similar

KEY = ("player_id", "season", "competition_id")


@dataclass(frozen=True)
class Brief:
    reference: Mapping[str, object]  # player_id, season, competition_id
    positions: Sequence[str]  # sub positions that can fill the role
    max_market_value: float
    max_age: float
    min_minutes: int
    exclude_club_ids: Sequence[int] = ()
    weights: Mapping[str, float] = field(default_factory=dict)
    top_similar: int = 10  # size of the "most similar" group the picks come from
    min_minutes_share: float = 0.6  # "already plays most of his team's minutes"
    value_floor_quantile: float = 0.75  # output floor for best_value (shortlist quantile)
    young_floor_quantile: float = 0.5  # output floor for younger_upside


def shortlist(players: pd.DataFrame, brief: Brief, *, comparison_min_minutes: int) -> pd.DataFrame:
    """Candidates meeting the brief, most similar first."""
    candidates = find_similar(
        players,
        brief.reference,
        min_minutes=comparison_min_minutes,
        weights=dict(brief.weights),
        seasons=[int(brief.reference["season"])],
        max_age=brief.max_age,
        max_market_value=brief.max_market_value,
        top_n=len(players),
    )
    mask = (
        candidates["sub_position"].isin(list(brief.positions))
        & (candidates["minutes"] >= brief.min_minutes)
        & ~candidates["club_id"].isin(list(brief.exclude_club_ids))
        & ~candidates["market_value_stale"].fillna(True).astype(bool)
    )
    return candidates[mask].reset_index(drop=True)


def pick_alternatives(candidates: pd.DataFrame, brief: Brief) -> pd.DataFrame:
    """Three distinct alternatives (see module docstring); fewer if the pool is too small."""
    if candidates.empty:
        return candidates.assign(pick=pd.Series(dtype="object"))
    top = candidates.head(brief.top_similar)
    score = candidates["performance_score"]

    def at_least(quantile: float) -> pd.DataFrame:
        return top[top["performance_score"] >= score.quantile(quantile)]

    picks: list[tuple[str, int]] = [("closest_profile", top.index[0])]

    def remaining(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[~frame.index.isin([i for _, i in picks])]

    value_pool = remaining(at_least(brief.value_floor_quantile)).dropna(subset=["value_ratio"])
    if not value_pool.empty:
        picks.append(("best_value", value_pool["value_ratio"].idxmin()))

    young_pool = remaining(at_least(brief.young_floor_quantile))
    young_pool = young_pool[young_pool["minutes_share"] >= brief.min_minutes_share]
    if not young_pool.empty:
        picks.append(("younger_upside", young_pool["age"].idxmin()))

    rows = candidates.loc[[i for _, i in picks]].copy()
    rows.insert(0, "pick", [name for name, _ in picks])
    return rows.reset_index(drop=True)
