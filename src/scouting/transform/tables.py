"""Load the Parquet extract and give every table consistent types.

The source stores the same id as an integer in one table and as text in another, seasons as text
and some dates as timestamps. After :func:`normalize`, ids are nullable ``Int64``, ``season`` is
an integer start year (2025 = 2025/26) and dates are ``datetime64`` at day precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TABLES = (
    "competitions",
    "clubs",
    "games",
    "european_games",
    "appearances",
    "game_events",
    "game_lineups",
    "players",
    "player_valuations",
    "transfers",
)

ID_COLUMNS = (
    "game_id",
    "player_id",
    "club_id",
    "player_club_id",
    "home_club_id",
    "away_club_id",
    "player_in_id",
    "player_assist_id",
    "current_club_id",
    "from_club_id",
    "to_club_id",
)
DATE_COLUMNS = ("date", "date_of_birth", "contract_expiration_date", "transfer_date")
INT_COLUMNS = (
    "minute",
    "minutes_played",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "home_club_goals",
    "away_club_goals",
    "height_in_cm",
)
FLOAT_COLUMNS = ("market_value_in_eur", "transfer_fee")
DATE_DTYPE = "datetime64[ns]"


@dataclass(frozen=True)
class Tables:
    """The extract with normalized types. One attribute per source table."""

    competitions: pd.DataFrame
    clubs: pd.DataFrame
    games: pd.DataFrame
    european_games: pd.DataFrame
    appearances: pd.DataFrame
    game_events: pd.DataFrame
    game_lineups: pd.DataFrame
    players: pd.DataFrame
    player_valuations: pd.DataFrame
    transfers: pd.DataFrame


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").round().astype("Int64")


def normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with ids, seasons, dates and numbers in consistent types."""
    out = df.copy()
    for column in out.columns:
        if column in ID_COLUMNS or column in INT_COLUMNS or column == "season":
            out[column] = _to_int(out[column])
        elif column in DATE_COLUMNS:
            out[column] = (
                pd.to_datetime(out[column], errors="coerce").dt.normalize().astype(DATE_DTYPE)
            )
        elif column in FLOAT_COLUMNS:
            out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
    return out


def normalize(raw: dict[str, pd.DataFrame]) -> Tables:
    """Normalize a dict of raw frames (as read from the extract) into :class:`Tables`."""
    missing = [name for name in TABLES if name not in raw]
    if missing:
        raise KeyError(f"Extract is missing tables: {missing}")
    return Tables(**{name: normalize_frame(raw[name]) for name in TABLES})


def load_tables(extract_dir: Path) -> Tables:
    """Read every table of the extract from ``extract_dir`` and normalize it."""
    raw = {}
    for name in TABLES:
        path = extract_dir / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run `python scripts/fetch_data.py` to build the extract."
            )
        raw[name] = pd.read_parquet(path)
    return normalize(raw)
