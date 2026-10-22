from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from conftest import make_source_db
from scouting.ingest import transfermarkt as tm


def _read(path: Path) -> list[tuple]:
    return duckdb.sql(f"select * from '{path.as_posix()}'").fetchall()


def _ids(path: Path, column: str) -> set[str]:
    """Ids as text: the extract keeps source types, which differ between tables."""
    rows = duckdb.sql(f"select cast({column} as varchar) from '{path.as_posix()}'").fetchall()
    return {row[0] for row in rows}


# --- extract -----------------------------------------------------------------------------------


@pytest.fixture
def extracted(source_db: Path, tmp_path: Path) -> tm.ExtractResult:
    return tm.extract(source_db, tmp_path / "out", ["PO1", "ES1"], [2025], source_url="https://x")


def test_extract_keeps_only_scope_games(extracted: tm.ExtractResult) -> None:
    assert _ids(extracted.out_dir / "games.parquet", "game_id") == {"100"}


def test_extract_handles_text_seasons(extracted: tm.ExtractResult) -> None:
    # season is VARCHAR in the source; game 101 (season '2020') must be excluded.
    assert "101" not in _ids(extracted.out_dir / "games.parquet", "game_id")


def test_extract_related_tables_follow_scope(extracted: tm.ExtractResult) -> None:
    out = extracted.out_dir
    assert _ids(out / "appearances.parquet", "appearance_id") == {"100_10", "100_11"}
    assert _ids(out / "game_events.parquet", "game_id") == {"100"}
    assert _ids(out / "game_lineups.parquet", "player_id") == {"10", "11"}
    assert _ids(out / "players.parquet", "player_id") == {"10", "11"}
    assert _ids(out / "player_valuations.parquet", "player_id") == {"10"}
    assert _ids(out / "transfers.parquet", "player_id") == {"10"}


def test_extract_includes_european_games_in_scope_seasons(extracted: tm.ExtractResult) -> None:
    assert _ids(extracted.out_dir / "european_games.parquet", "game_id") == {"103"}


def test_extract_keeps_reference_tables_whole(extracted: tm.ExtractResult) -> None:
    assert len(_read(extracted.out_dir / "competitions.parquet")) == 4
    assert len(_read(extracted.out_dir / "clubs.parquet")) == 3


def test_manifest_records_scope_counts_and_checksum(
    source_db: Path, extracted: tm.ExtractResult
) -> None:
    manifest = json.loads(extracted.manifest_path.read_text(encoding="utf-8"))
    assert manifest["competitions"] == ["PO1", "ES1"]
    assert manifest["seasons"] == [2025]
    assert manifest["row_counts"] == extracted.row_counts
    assert manifest["row_counts"]["games"] == 1
    assert manifest["source_sha256"] == tm.sha256_of(source_db)
    assert manifest["source_version"][0]["version"] == "2026-07-06"


def test_extract_fails_clearly_on_schema_change(tmp_path: Path) -> None:
    db = make_source_db(tmp_path / "bad.duckdb", drop_column=("appearances", "minutes_played"))
    with pytest.raises(tm.SourceSchemaError, match="minutes_played"):
        tm.extract(db, tmp_path / "out", ["PO1"], [2025])


def test_extract_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        tm.extract(tmp_path / "missing.duckdb", tmp_path / "out", ["PO1"], [2025])


def test_extract_does_not_modify_source(source_db: Path, tmp_path: Path) -> None:
    before = tm.sha256_of(source_db)
    tm.extract(source_db, tmp_path / "out", ["PO1"], [2025])
    assert tm.sha256_of(source_db) == before


# --- download ----------------------------------------------------------------------------------

PAYLOAD = [b"chunk-1", b"chunk-2"]
PAYLOAD_SHA = hashlib.sha256(b"".join(PAYLOAD)).hexdigest()


class FakeFetch:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.calls = 0

    def __call__(self, url: str):
        self.calls += 1
        yield from self.chunks


def test_download_writes_file(tmp_path: Path) -> None:
    fetch = FakeFetch(PAYLOAD)
    dest = tm.download("https://x/db", tmp_path / "raw" / "db.duckdb", PAYLOAD_SHA, fetch=fetch)
    assert dest.read_bytes() == b"chunk-1chunk-2"
    assert fetch.calls == 1


def test_download_uses_cache(tmp_path: Path) -> None:
    dest = tmp_path / "db.duckdb"
    fetch = FakeFetch(PAYLOAD)
    tm.download("https://x/db", dest, PAYLOAD_SHA, fetch=fetch)
    tm.download("https://x/db", dest, PAYLOAD_SHA, fetch=fetch)
    tm.download("https://x/db", dest, None, fetch=fetch)
    assert fetch.calls == 1


def test_download_force_refetches(tmp_path: Path) -> None:
    dest = tmp_path / "db.duckdb"
    fetch = FakeFetch(PAYLOAD)
    tm.download("https://x/db", dest, fetch=fetch)
    tm.download("https://x/db", dest, fetch=fetch, force=True)
    assert fetch.calls == 2


def test_download_rejects_checksum_mismatch_and_keeps_no_partial_file(tmp_path: Path) -> None:
    dest = tmp_path / "db.duckdb"
    with pytest.raises(tm.ChecksumMismatchError):
        tm.download("https://x/db", dest, "0" * 64, fetch=FakeFetch(PAYLOAD))
    assert list(tmp_path.iterdir()) == []


def test_download_replaces_cache_that_fails_checksum(tmp_path: Path) -> None:
    dest = tmp_path / "db.duckdb"
    dest.write_bytes(b"stale")
    fetch = FakeFetch(PAYLOAD)
    tm.download("https://x/db", dest, PAYLOAD_SHA, fetch=fetch)
    assert fetch.calls == 1
    assert dest.read_bytes() == b"chunk-1chunk-2"


# --- script ------------------------------------------------------------------------------------


def test_fetch_script_runs_end_to_end_with_local_db(
    source_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    import importlib.util

    import yaml

    from scouting.config import DEFAULT_CONFIG_PATH

    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["scope"]["seasons"] = [2025]
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "fetch_data.py"
    spec = importlib.util.spec_from_file_location("fetch_data", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main(["--config", str(config_dir / "settings.yaml"), "--db", str(source_db)]) == 0
    assert (tmp_path / "data" / "processed" / "transfermarkt" / "manifest.json").exists()
    assert "games" in capsys.readouterr().out
