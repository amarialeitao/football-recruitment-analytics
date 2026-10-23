"""Everything the app shows, computed once from the local data (no Streamlit here).

``build_app_data`` reads the extract and the player-season table, adds percentiles and the
value model, and computes league strength, coverage and the quality summary. The UI wraps it
in a single cached loader (:mod:`scouting.ui.data`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from scouting.config import Settings
from scouting.metrics.league_strength import league_strength
from scouting.metrics.percentiles import percentile_ranks
from scouting.metrics.value import expected_value
from scouting.quality import QualitySummary, coverage, summarize
from scouting.transform.player_season import build_player_season
from scouting.transform.tables import load_tables

PLAYER_SEASON_FILE = "player_season.parquet"
EXTRACT_DIR = "transfermarkt"


class DataNotReadyError(RuntimeError):
    """The local data has not been built yet; the message says which command to run."""


@dataclass(frozen=True)
class AppData:
    players: pd.DataFrame  # player x season x competition, with percentiles and value columns
    valuations: pd.DataFrame  # market value history of those players
    league_strength: pd.DataFrame
    coverage: pd.DataFrame
    quality: QualitySummary
    manifest: dict
    data_cutoff: pd.Timestamp

    @property
    def seasons(self) -> list[int]:
        return sorted(self.players["season"].dropna().unique().tolist())


def build_app_data(settings: Settings, *, today: pd.Timestamp) -> AppData:
    """Load and enrich the local data. Raises :class:`DataNotReadyError` if it is missing."""
    extract_dir = settings.processed_dir / EXTRACT_DIR
    if not (extract_dir / "manifest.json").exists():
        raise DataNotReadyError(
            "No local data found. Run `python scripts/fetch_data.py` and then "
            "`python scripts/build_dataset.py`."
        )
    tables = load_tables(extract_dir)

    table_path = settings.processed_dir / PLAYER_SEASON_FILE
    players = pd.read_parquet(table_path) if table_path.exists() else build_player_season(tables)

    min_minutes = settings.analysis.min_minutes
    strength = league_strength(
        players,
        tables.european_games,
        tables.games,
        tables.clubs,
        settings.scope.focus_competition,
    )
    enriched = expected_value(
        percentile_ranks(players, min_minutes=min_minutes), strength, min_minutes=min_minutes
    )
    names = settings.scope.competitions
    enriched["competition_name"] = enriched["competition_id"].map(names)
    strength = strength.assign(competition_name=strength["competition_id"].map(names))

    manifest = json.loads((extract_dir / "manifest.json").read_text(encoding="utf-8"))
    valuations = tables.player_valuations.loc[
        tables.player_valuations["player_id"].isin(players["player_id"]),
        ["player_id", "date", "market_value_in_eur"],
    ].sort_values(["player_id", "date"])
    return AppData(
        players=enriched,
        valuations=valuations.reset_index(drop=True),
        league_strength=strength,
        coverage=coverage(tables, players, min_minutes),
        quality=summarize(tables, enriched, min_minutes=min_minutes, today=today),
        manifest=manifest,
        data_cutoff=pd.Timestamp(tables.games["date"].max()),
    )


def extract_dir(settings: Settings) -> Path:
    return settings.processed_dir / EXTRACT_DIR
