"""Build the analysis table (player x season x competition) from the local extract.

Usage:
    python scripts/build_dataset.py            # reads data/processed/transfermarkt
    python scripts/build_dataset.py --config path/to/settings.yaml
"""

from __future__ import annotations

import argparse

from scouting.config import load_settings
from scouting.transform.player_season import build_player_season
from scouting.transform.stints import build_stints
from scouting.transform.tables import load_tables

OUTPUT_NAME = "player_season.parquet"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Path to settings.yaml (default: config/settings.yaml)")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    extract_dir = settings.processed_dir / "transfermarkt"
    tables = load_tables(extract_dir)

    stints = build_stints(tables.games, tables.appearances, tables.game_lineups, tables.game_events)
    table = build_player_season(tables, stints)

    out = settings.processed_dir / OUTPUT_NAME
    table.to_parquet(out, index=False)

    unreconciled = int((~stints.drop_duplicates("game_id")["events_reconciled"]).sum())
    print(f"Rows: {len(table):,} player-seasons -> {out}")
    print(f"Games whose goal events do not match the score: {unreconciled} (on-pitch goals empty)")
    summary = (
        table.assign(over_900=table["minutes"] >= 900)
        .groupby(["competition_id", "season_label"])
        .agg(players=("player_id", "size"), players_900=("over_900", "sum"))
    )
    print(summary.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
