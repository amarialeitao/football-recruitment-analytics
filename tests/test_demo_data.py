"""Hosted-demo data: packaging, safe unpacking and the first-start download. No network."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scouting.config import DemoDataSource, load_settings
from scouting.ingest import demo_data as demo
from scouting.ingest.transfermarkt import ChecksumMismatchError, sha256_of

ON = {demo.ENV_VAR: "true"}


@pytest.fixture
def processed(tmp_path: Path) -> Path:
    root = tmp_path / "built"
    (root / "transfermarkt").mkdir(parents=True)
    (root / "transfermarkt" / "manifest.json").write_text('{"source": "x"}')
    (root / "transfermarkt" / "games.parquet").write_bytes(b"games")
    (root / "player_season.parquet").write_bytes(b"players")
    return root


@pytest.fixture
def archive(processed: Path, tmp_path: Path) -> Path:
    return demo.package(processed, tmp_path / "zips" / "demo.zip")


def _settings(tmp_path: Path, archive: Path | None):
    settings = load_settings()
    source = None
    if archive is not None:
        source = DemoDataSource(url="https://example.org/demo.zip", sha256=sha256_of(archive))
    return settings.model_copy(
        update={
            "root": tmp_path / "app",
            "sources": settings.sources.model_copy(update={"demo_data": source}),
        }
    )


def _fetch(archive: Path):
    def fetch(url: str):
        yield archive.read_bytes()

    return fetch


def test_package_is_deterministic(processed: Path, tmp_path: Path, archive: Path) -> None:
    again = demo.package(processed, tmp_path / "again.zip")
    assert sha256_of(again) == sha256_of(archive)
    assert zipfile.ZipFile(archive).namelist() == [
        "transfermarkt/games.parquet",
        "transfermarkt/manifest.json",
        "player_season.parquet",
    ]


def test_package_requires_built_data(tmp_path: Path) -> None:
    with pytest.raises(demo.DemoDataError, match="fetch_data"):
        demo.package(tmp_path, tmp_path / "x.zip")
    (tmp_path / "transfermarkt").mkdir()
    (tmp_path / "transfermarkt" / "manifest.json").write_text("{}")
    with pytest.raises(demo.DemoDataError, match="build_dataset"):
        demo.package(tmp_path, tmp_path / "x.zip")


@pytest.mark.parametrize(
    "name", ["../evil.parquet", "/etc/passwd", "transfermarkt/x.py", "notes.txt"]
)
def test_unpack_rejects_unexpected_members(tmp_path: Path, name: str) -> None:
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("player_season.parquet", b"x")
        archive.writestr(name, b"x")
    with pytest.raises(demo.DemoDataError, match="Unexpected"):
        demo.unpack(bad, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_unpack_requires_core_files(tmp_path: Path) -> None:
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("transfermarkt/games.parquet", b"x")
    with pytest.raises(demo.DemoDataError, match="missing"):
        demo.unpack(bad, tmp_path / "out")


def test_disabled_by_default(tmp_path: Path, archive: Path) -> None:
    assert not demo.demo_enabled({})
    assert demo.ensure_demo_data(_settings(tmp_path, archive), env={}) is False


def test_downloads_verifies_and_unpacks(tmp_path: Path, archive: Path) -> None:
    settings = _settings(tmp_path, archive)
    assert demo.ensure_demo_data(settings, env=ON, fetch=_fetch(archive)) is True
    assert (settings.processed_dir / "transfermarkt" / "manifest.json").exists()
    assert (settings.processed_dir / "player_season.parquet").read_bytes() == b"players"
    # Second start: local data exists, nothing is downloaded.
    assert demo.ensure_demo_data(settings, env=ON, fetch=None) is False


def test_new_release_replaces_installed_demo_data(tmp_path: Path, processed: Path) -> None:
    v1 = demo.package(processed, tmp_path / "v1.zip")
    settings = _settings(tmp_path, v1)
    assert demo.ensure_demo_data(settings, env=ON, fetch=_fetch(v1)) is True

    (processed / "player_season.parquet").write_bytes(b"players v2")
    v2 = demo.package(processed, tmp_path / "v2.zip")
    newer = _settings(tmp_path, v2)
    assert demo.ensure_demo_data(newer, env=ON, fetch=_fetch(v2)) is True
    assert (newer.processed_dir / "player_season.parquet").read_bytes() == b"players v2"
    marker = newer.processed_dir / demo.MARKER_FILE
    assert marker.read_text(encoding="utf-8") == sha256_of(v2)
    assert demo.ensure_demo_data(newer, env=ON, fetch=None) is False  # already on v2


def test_locally_built_data_is_never_replaced(tmp_path: Path, archive: Path) -> None:
    settings = _settings(tmp_path, archive)
    extract = settings.processed_dir / "transfermarkt"
    extract.mkdir(parents=True)
    (extract / "manifest.json").write_text("{}")  # pipeline output, no demo marker
    assert demo.ensure_demo_data(settings, env=ON, fetch=None) is False
    assert (extract / "manifest.json").read_text() == "{}"


def test_checksum_mismatch_installs_nothing(tmp_path: Path, archive: Path) -> None:
    settings = _settings(tmp_path, archive)

    def tampered(url: str):
        yield archive.read_bytes() + b"x"

    with pytest.raises(ChecksumMismatchError):
        demo.ensure_demo_data(settings, env=ON, fetch=tampered)
    assert not settings.processed_dir.exists()


def test_enabled_without_source_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(demo.DemoDataError, match="not configured"):
        demo.ensure_demo_data(_settings(tmp_path, None), env=ON)


def test_project_config_pins_the_demo_archive() -> None:
    source = load_settings().sources.demo_data
    assert source is not None
    assert source.url.startswith("https://github.com/")
    assert len(source.sha256) == 64


def test_flag_accepts_toml_boolean_rendering() -> None:
    # st.secrets returns a bool for `SCOUTING_DEMO_DATA = true`; str(True) is "True".
    assert demo.demo_enabled({demo.ENV_VAR: str(True)})
    assert not demo.demo_enabled({demo.ENV_VAR: "false"})


def test_ui_reads_flag_from_streamlit_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    from scouting.ui import data as ui_data

    monkeypatch.delenv(demo.ENV_VAR, raising=False)
    monkeypatch.setattr(ui_data.st, "secrets", {demo.ENV_VAR: True})
    assert demo.demo_enabled(ui_data._demo_env())

    class NoSecrets:
        def get(self, key):
            raise FileNotFoundError("no secrets.toml")

    monkeypatch.setattr(ui_data.st, "secrets", NoSecrets())
    assert not demo.demo_enabled(ui_data._demo_env())
