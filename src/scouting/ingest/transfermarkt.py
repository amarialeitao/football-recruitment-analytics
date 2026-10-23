"""Transfermarkt loader: download the public DuckDB file once, then extract the project scope.

Source: transfermarkt-datasets (CC0 1.0). The raw file is cached locally and never committed.
The extract keeps only the configured competitions and seasons, plus the related players,
valuations and transfers, and writes one Parquet file per table with a ``manifest.json``.

Note: in the source database ``games.season`` is stored as text, so it is always cast.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import requests

CHUNK_SIZE = 1 << 20
USER_AGENT = "football-recruitment-analytics (portfolio project; single cached download)"

# Columns the rest of the pipeline relies on. A missing one means the source schema changed.
REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "competitions": ("competition_id", "name", "type", "country_name"),
    "clubs": ("club_id", "name", "domestic_competition_id"),
    "games": (
        "game_id",
        "competition_id",
        "season",
        "date",
        "home_club_id",
        "away_club_id",
        "home_club_goals",
        "away_club_goals",
    ),
    "appearances": (
        "appearance_id",
        "game_id",
        "player_id",
        "player_club_id",
        "competition_id",
        "minutes_played",
        "goals",
        "assists",
        "yellow_cards",
        "red_cards",
    ),
    "game_events": ("game_id", "minute", "type", "club_id", "player_id", "player_in_id"),
    "game_lineups": ("game_id", "player_id", "club_id", "type", "position"),
    "players": (
        "player_id",
        "name",
        "date_of_birth",
        "position",
        "sub_position",
        "foot",
        "height_in_cm",
        "country_of_citizenship",
        "current_club_id",
        "contract_expiration_date",
        "market_value_in_eur",
    ),
    "player_valuations": ("player_id", "date", "market_value_in_eur"),
    "transfers": ("player_id", "transfer_date", "from_club_id", "to_club_id", "transfer_fee"),
}

_SEASON = "try_cast(g.season as integer)"


class SourceSchemaError(RuntimeError):
    """The source database does not have the tables or columns this project expects."""


class ChecksumMismatchError(RuntimeError):
    """The downloaded file does not match the pinned checksum."""


@dataclass(frozen=True)
class ExtractResult:
    """Where the extract was written and how many rows each table has."""

    out_dir: Path
    row_counts: dict[str, int]
    manifest_path: Path


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream(url: str) -> Iterator[bytes]:
    with requests.get(url, stream=True, timeout=60, headers={"User-Agent": USER_AGENT}) as resp:
        resp.raise_for_status()
        yield from resp.iter_content(CHUNK_SIZE)


def download(
    url: str,
    dest: Path,
    expected_sha256: str | None = None,
    *,
    force: bool = False,
    fetch: Callable[[str], Iterable[bytes]] = _stream,
) -> Path:
    """Download ``url`` to ``dest`` unless a valid cached copy already exists.

    The file is written to a temporary name and only moved into place once complete (and, when
    ``expected_sha256`` is given, verified), so an interrupted download never leaves a bad cache.
    """
    cached = dest.exists() and not force
    if cached and (expected_sha256 is None or sha256_of(dest) == expected_sha256):
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    try:
        with tmp.open("wb") as handle:
            for chunk in fetch(url):
                handle.write(chunk)
                digest.update(chunk)
        actual = digest.hexdigest()
        if expected_sha256 is not None and actual != expected_sha256:
            raise ChecksumMismatchError(
                f"Checksum mismatch for {url}: expected {expected_sha256}, got {actual}. "
                "The source may have published a new version; update the pinned sha256 "
                "in config/settings.yaml if you want to use it."
            )
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def check_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Raise :class:`SourceSchemaError` listing every missing table or column."""
    rows = con.execute("select table_name, column_name from information_schema.columns").fetchall()
    present: dict[str, set[str]] = {}
    for table, column in rows:
        present.setdefault(table, set()).add(column)

    problems = []
    for table, columns in REQUIRED_COLUMNS.items():
        if table not in present:
            problems.append(f"missing table '{table}'")
            continue
        missing = [c for c in columns if c not in present[table]]
        if missing:
            problems.append(f"table '{table}' is missing columns {missing}")
    if problems:
        raise SourceSchemaError("Unexpected source schema: " + "; ".join(problems))


def _sql_list(values: Iterable[object]) -> str:
    items = []
    for value in values:
        if isinstance(value, int):
            items.append(str(value))
        else:
            items.append("'" + str(value).replace("'", "''") + "'")
    return "(" + ", ".join(items) + ")"


def _queries(competitions: list[str], seasons: list[int]) -> dict[str, str]:
    comps = _sql_list(competitions)
    years = _sql_list(seasons)
    games = f"select g.* from games g where g.competition_id in {comps} and {_SEASON} in {years}"
    # Id columns do not share one type across source tables (integer in some, text in others),
    # so every id comparison is made on the text form of both sides.
    game_ids = f"(select cast(game_id as varchar) from ({games}))"
    player_ids = (
        "(select distinct cast(player_id as varchar) from appearances "
        f"where cast(game_id as varchar) in {game_ids})"
    )
    by_game = f"where cast(game_id as varchar) in {game_ids}"
    by_player = f"where cast(player_id as varchar) in {player_ids}"
    # European club competitions in the same seasons: used later to estimate league strength.
    european_games = f"""
        select g.* from games g join competitions c using (competition_id)
        where c.type = 'international_cup' and {_SEASON} in {years}"""
    return {
        "competitions": "select * from competitions",
        "clubs": "select * from clubs",
        "games": games,
        "european_games": european_games,
        "appearances": f"select * from appearances {by_game}",
        "game_events": f"select * from game_events {by_game}",
        "game_lineups": f"select * from game_lineups {by_game}",
        "players": f"select * from players {by_player}",
        "player_valuations": f"select * from player_valuations {by_player}",
        "transfers": f"select * from transfers {by_player}",
    }


def _source_version(con: duckdb.DuckDBPyConnection) -> list[dict[str, object]] | None:
    tables = {
        row[0] for row in con.execute("select table_name from information_schema.tables").fetchall()
    }
    if "version" not in tables:
        return None
    df = con.execute("select * from version").df()
    return json.loads(df.to_json(orient="records", date_format="iso"))


def extract(
    db_path: Path,
    out_dir: Path,
    competitions: list[str],
    seasons: list[int],
    *,
    source_url: str | None = None,
) -> ExtractResult:
    """Export the project scope from the source DuckDB file to Parquet, one file per table."""
    if not db_path.exists():
        raise FileNotFoundError(f"Source database not found: {db_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        check_schema(con)
        counts: dict[str, int] = {}
        for table, query in _queries(competitions, seasons).items():
            target = out_dir / f"{table}.parquet"
            con.execute(f"copy ({query}) to '{target.as_posix()}' (format parquet)")
            counts[table] = con.execute(f"select count(*) from '{target.as_posix()}'").fetchone()[0]
        version = _source_version(con)
    finally:
        con.close()

    manifest = {
        "source": "transfermarkt-datasets",
        "source_url": source_url,
        "source_sha256": sha256_of(db_path),
        "source_version": version,
        "competitions": competitions,
        "seasons": seasons,
        "row_counts": counts,
        "extracted_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return ExtractResult(out_dir=out_dir, row_counts=counts, manifest_path=manifest_path)
