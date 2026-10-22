"""Download the source data and build the local Parquet extract.

Usage:
    python scripts/fetch_data.py                      # download (cached) + extract
    python scripts/fetch_data.py --db path/to.duckdb  # use a file you already have
    python scripts/fetch_data.py --force              # re-download even if cached
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scouting.config import load_settings
from scouting.ingest import transfermarkt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--config", help="Path to settings.yaml (default: config/settings.yaml)")
    parser.add_argument(
        "--db", type=Path, help="Use an existing DuckDB file instead of downloading"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if a cached copy exists"
    )
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    source = settings.sources.transfermarkt

    if args.db:
        db_path = args.db
    else:
        db_path = settings.raw_dir / source.filename
        print(f"Source: {source.url}")
        transfermarkt.download(source.url, db_path, source.sha256, force=args.force)
    print(f"Using {db_path}")

    result = transfermarkt.extract(
        db_path,
        settings.processed_dir / "transfermarkt",
        settings.scope.competition_ids,
        settings.scope.seasons,
        source_url=source.url,
    )
    width = max(len(name) for name in result.row_counts)
    for table, rows in result.row_counts.items():
        print(f"  {table:<{width}}  {rows:>10,}")
    print(f"Manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
