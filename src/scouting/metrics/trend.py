"""Season-over-season change: is the player improving or declining against his peers?

The comparison uses percentiles, not raw values, because each season's percentiles already
compare the player with the same kind of peers (same position group, all leagues in scope,
minimum minutes). "Start rate up from 60 to 89" therefore means he moved up among regulars in
his position, not just that his team played differently.

Rules:

* Both seasons need at least the minimum minutes; otherwise there is no percentile to compare
  and the page says so instead of guessing.
* The previous season is the player's previous season in the leagues in scope (any league).
  If he played in two leagues that season, the one where he played most is used.
* A change counts as "improved" or "declined" only if it moves at least ``threshold``
  percentile points (``analysis.trend_min_change`` in the configuration); smaller moves are
  "about the same". Percentiles are oriented so 100 is best, so for "lower is better" metrics
  (cards, goals conceded) "improved" means fewer.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from scouting.insights import Insight, confidence_from_sample, format_int
from scouting.metrics.catalog import metric
from scouting.metrics.percentiles import PCT_SUFFIX

UP, DOWN, SAME = "up", "down", "same"


def previous_season(players: pd.DataFrame, row: pd.Series) -> pd.Series | None:
    """The player's row for the season before ``row`` (most minutes if several leagues)."""
    earlier = players[
        (players["player_id"] == row["player_id"]) & (players["season"] == int(row["season"]) - 1)
    ]
    if earlier.empty:
        return None
    return earlier.sort_values("minutes", ascending=False).iloc[0]


def season_changes(
    current: pd.Series, previous: pd.Series, keys: Sequence[str], *, threshold: float
) -> pd.DataFrame:
    """One row per metric: previous and current percentile, change and direction.

    Metrics without a percentile in either season are left out.
    """
    rows = []
    for key in keys:
        before, now = previous.get(key + PCT_SUFFIX), current.get(key + PCT_SUFFIX)
        if before is None or now is None or pd.isna(before) or pd.isna(now):
            continue
        change = float(now) - float(before)
        direction = UP if change >= threshold else DOWN if change <= -threshold else SAME
        rows.append(
            {
                "metric": key,
                "previous_pct": float(before),
                "current_pct": float(now),
                "change": change,
                "direction": direction,
            }
        )
    out = pd.DataFrame(
        rows, columns=["metric", "previous_pct", "current_pct", "change", "direction"]
    )
    # Biggest moves first, so the page leads with what changed most.
    return out.reindex(out["change"].abs().sort_values(ascending=False).index).reset_index(
        drop=True
    )


def change_insights(
    changes: pd.DataFrame,
    *,
    current: pd.Series,
    previous: pd.Series,
    confidence_minutes: tuple[int, int],
) -> list[Insight]:
    """Plain sentences: one per clear change, plus one listing what stayed about the same."""
    medium, high = confidence_minutes
    # The weaker of the two seasons decides how sure we can be about the change.
    confidence = confidence_from_sample(
        current["minutes"], previous["minutes"], medium=medium, high=high
    )
    evidence = {
        "previous_minutes": int(previous["minutes"]),
        "current_minutes": int(current["minutes"]),
    }
    out: list[Insight] = []
    # Percentiles are oriented so 100 is always best, so "improved" is right even for metrics
    # where a lower raw value is better (fewer cards, fewer goals conceded).
    for rank, item in enumerate(changes[changes["direction"] != SAME].itertuples()):
        m = metric(item.metric)
        move = f"{round(item.previous_pct)} → {round(item.current_pct)}"
        if item.direction == UP:
            en, pt = f"improved, percentile {move}", f"melhorou, percentil {move}"
        else:
            en, pt = f"declined, percentile {move}", f"piorou, percentil {move}"
        out.append(
            Insight(
                # The rank in the key keeps the biggest change first when the page sorts.
                key=f"trend:{rank:02d}:{item.metric}",
                text={"en": f"{m.label_for('en')}: {en}.", "pt": f"{m.label_for('pt')}: {pt}."},
                confidence=confidence,
                kind="observation",
                sample=min(evidence.values()),
                evidence={**evidence, "metric": item.metric},
            )
        )
    same = changes[changes["direction"] == SAME]
    if not same.empty:
        names = {
            lang: ", ".join(metric(k).label_for(lang).lower() for k in same["metric"])
            for lang in ("en", "pt")
        }
        out.append(
            Insight(
                key="trend:99:same",
                text={
                    "en": f"About the same as last season: {names['en']}.",
                    "pt": f"Praticamente igual à época anterior: {names['pt']}.",
                },
                confidence=confidence,
                kind="observation",
                sample=min(evidence.values()),
                evidence=evidence,
            )
        )
    return out


def minutes_note(previous: pd.Series | None, min_minutes: int, lang: str) -> str | None:
    """Why there is no comparison, in plain words (None when a comparison is possible)."""
    if previous is None:
        return {
            "en": "No previous season in the leagues in scope, so there is nothing to compare.",
            "pt": "Sem época anterior nas ligas analisadas, por isso não há comparação.",
        }[lang]
    if previous["minutes"] < min_minutes:
        played = format_int(int(previous["minutes"]), lang)
        return {
            "en": f"Only {played} league minutes last season (below {min_minutes}), too few "
            "to compare percentiles.",
            "pt": f"Só {played} minutos de liga na época anterior (abaixo de {min_minutes}), "
            "poucos para comparar percentis.",
        }[lang]
    return None
