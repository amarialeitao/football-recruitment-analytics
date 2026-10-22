"""Data-quality checks: light enough to recompute every time the app loads.

Each function answers one question and returns numbers only; wording lives in
:mod:`scouting.health` and the UI.

Key fields are the ones filled at registration for every player (age, position, foot, height,
market value). Absence of a contract date is reported separately: it is expected for players
without a club or on loan, so counting it as missing data would confuse "no contract on record"
with "bad data".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from scouting.metrics.value import STALE_DAYS
from scouting.transform.stints import reconcile_goal_events
from scouting.transform.tables import Tables

KEY_FIELDS: tuple[str, ...] = (
    "date_of_birth",
    "position_group",
    "foot",
    "height_in_cm",
    "market_value_end",
)
FIELD_LABELS: dict[str, dict[str, str]] = {
    "date_of_birth": {"en": "date of birth", "pt": "data de nascimento"},
    "position_group": {"en": "position", "pt": "posição"},
    "foot": {"en": "preferred foot", "pt": "pé preferido"},
    "height_in_cm": {"en": "height", "pt": "altura"},
    "market_value_end": {"en": "market value", "pt": "valor de mercado"},
}
KEY = ["player_id", "season", "competition_id"]


@dataclass(frozen=True)
class QualitySummary:
    """All quality numbers the status board and the Data Quality page need."""

    data_cutoff: pd.Timestamp
    games: int
    unreconciled_games: int
    player_seasons: int
    duplicate_keys: int
    completeness: dict[str, float]
    contract_missing_share: float
    stale_value_share: float
    below_min_minutes_share: float
    future_transfers: int
    smallest_comparison_group: int | None

    @property
    def completeness_min(self) -> tuple[str, float]:
        """The worst key field and its fill rate."""
        field = min(self.completeness, key=self.completeness.get)
        return field, self.completeness[field]

    @property
    def unreconciled_share(self) -> float:
        return self.unreconciled_games / self.games if self.games else 0.0


def data_cutoff(tables: Tables) -> pd.Timestamp:
    """Date of the most recent game in the extract."""
    return pd.Timestamp(tables.games["date"].max())


def coverage(tables: Tables, player_season: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    """Games, clubs and players per competition and season."""
    games = tables.games.groupby(["competition_id", "season"]).agg(
        games=("game_id", "nunique"),
        first_game=("date", "min"),
        last_game=("date", "max"),
    )
    players = player_season.groupby(["competition_id", "season"]).agg(
        clubs=("club_id", "nunique"),
        players=("player_id", "nunique"),
        players_min_minutes=("minutes", lambda m: int((m >= min_minutes).sum())),
    )
    return games.join(players, how="outer").reset_index()


def field_completeness(
    player_season: pd.DataFrame, fields: tuple[str, ...] = KEY_FIELDS
) -> dict[str, float]:
    """Share of non-missing values per key field among player-seasons with minutes."""
    present = [f for f in fields if f in player_season.columns]
    if player_season.empty:
        return {f: 1.0 for f in present}
    return {f: float(player_season[f].notna().mean()) for f in present}


def stale_value_share(player_season: pd.DataFrame, min_minutes: int) -> float:
    """Share of regulars whose end-of-season market value is older than ``STALE_DAYS``."""
    regulars = player_season[player_season["minutes"] >= min_minutes]
    if regulars.empty:
        return 0.0
    season_end = pd.to_datetime((regulars["season"] + 1).astype(str) + "-06-30")
    age_days = (season_end - pd.to_datetime(regulars["market_value_end_date"])).dt.days
    return float((age_days.isna() | (age_days > STALE_DAYS)).mean())


def future_transfers(tables: Tables, today: pd.Timestamp) -> pd.DataFrame:
    """Transfers dated after ``today``: impossible dates, usually loan ends or source errors."""
    transfers = tables.transfers
    return transfers[transfers["transfer_date"] > today.normalize()]


def summarize(
    tables: Tables, player_season: pd.DataFrame, *, min_minutes: int, today: pd.Timestamp
) -> QualitySummary:
    """Compute every quality number in one pass."""
    cutoff = data_cutoff(tables)
    reconciled = reconcile_goal_events(tables.games, tables.game_events)
    comparison = player_season.get("comparison_n")
    smallest = (
        int(comparison.min()) if comparison is not None and comparison.notna().any() else None
    )
    contract = player_season["contract_expiration_date"]
    return QualitySummary(
        data_cutoff=cutoff,
        games=int(tables.games["game_id"].nunique()),
        unreconciled_games=int((~reconciled).sum()),
        player_seasons=len(player_season),
        duplicate_keys=int(player_season.duplicated(KEY).sum()),
        completeness=field_completeness(player_season),
        contract_missing_share=float(contract.isna().mean()) if len(contract) else 0.0,
        stale_value_share=stale_value_share(player_season, min_minutes),
        below_min_minutes_share=float((player_season["minutes"] < min_minutes).mean()),
        future_transfers=len(future_transfers(tables, today)),
        smallest_comparison_group=smallest,
    )
