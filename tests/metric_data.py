"""Synthetic player-season frames for metric tests. All values are invented."""

from __future__ import annotations

import numpy as np
import pandas as pd

GROUPS = ["Forward", "Midfielder", "Defender", "Goalkeeper"]


def synthetic_player_season(n_per_group: int = 60, seed: int = 7) -> pd.DataFrame:
    """Player-seasons with every column the metrics read. Market value grows with output."""
    rng = np.random.default_rng(seed)
    rows = []
    pid = 1
    for group in GROUPS:
        for i in range(n_per_group):
            minutes = int(rng.integers(300, 3200))
            quality = rng.uniform(0, 1)
            age = float(rng.uniform(18, 34))
            comp = ["AA1", "BB1"][i % 2]
            rows.append(
                {
                    "player_id": pid,
                    "season": 2025,
                    "competition_id": comp,
                    "club_id": 100 + i % 10,
                    "position_group": group,
                    "minutes": minutes,
                    "minutes_share": minutes / 3060,
                    "start_rate": min(1.0, 0.3 + quality * 0.7),
                    "goals_p90": quality * 0.6 if group != "Goalkeeper" else 0.0,
                    "assists_p90": quality * 0.3,
                    "goal_contributions_p90": quality * 0.9,
                    "goals_for_on_p90": 1 + quality,
                    "goals_against_on_p90": 2 - quality,
                    "plus_minus_on_p90": 2 * quality - 1,
                    "yellow_cards_p90": rng.uniform(0, 0.4),
                    "age": age,
                    "market_value_start": 1e6 * (1 + quality * 4),
                    "market_value_end": 1e6 * (1 + quality * 9) * (1.5 if comp == "AA1" else 1),
                    "market_value_end_date": pd.Timestamp("2026-05-01"),
                }
            )
            pid += 1
    return pd.DataFrame(rows)
