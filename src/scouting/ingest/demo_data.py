"""Prebuilt data for a hosted demo, so a server can run the app without the full pipeline.

The repository never contains data. For a hosted demo (Streamlit Community Cloud), the processed
extract and the player-season table are packaged once into a zip with
``scripts/package_demo_data.py`` and attached to a GitHub release. On first start, the app
downloads that zip, checks its SHA-256 against ``sources.demo_data`` in ``config/settings.yaml``
and unpacks it into ``data/processed``.

This only happens when the ``SCOUTING_DEMO_DATA`` environment variable is set, so running the
app locally always uses data you built yourself. When ``sources.demo_data`` points to a new
archive, the server replaces its copy on the next start.
"""

from __future__ import annotations

import os
import re
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path

from scouting.config import Settings
from scouting.ingest.transfermarkt import _stream, download

ENV_VAR = "SCOUTING_DEMO_DATA"
EXTRACT_DIR = "transfermarkt"
PLAYER_SEASON_FILE = "player_season.parquet"
MARKER_FILE = ".demo-data-sha256"  # checksum of the installed demo archive
# Fixed timestamp so the same files always give the same zip (and the same checksum).
_ZIP_DATE = (2020, 1, 1, 0, 0, 0)
_MEMBER = re.compile(rf"^(?:{EXTRACT_DIR}/[a-z_]+\.(?:parquet|json)|{PLAYER_SEASON_FILE})$")


class DemoDataError(RuntimeError):
    """The demo archive is missing files or contains something it should not."""


def demo_enabled(env: dict[str, str] | None = None) -> bool:
    value = (os.environ if env is None else env).get(ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _members(processed_dir: Path) -> list[Path]:
    extract = processed_dir / EXTRACT_DIR
    if not (extract / "manifest.json").exists():
        raise DemoDataError(f"No extract in {extract}. Run fetch_data.py first.")
    if not (processed_dir / PLAYER_SEASON_FILE).exists():
        raise DemoDataError(f"No {PLAYER_SEASON_FILE} in {processed_dir}. Run build_dataset.py.")
    files = sorted(
        p for p in extract.iterdir() if p.is_file() and p.suffix in {".parquet", ".json"}
    )
    return [*files, processed_dir / PLAYER_SEASON_FILE]


def package(processed_dir: Path, out_zip: Path) -> Path:
    """Zip the processed data deterministically (same input, same bytes)."""
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _members(processed_dir):
            info = zipfile.ZipInfo(path.relative_to(processed_dir).as_posix(), _ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return out_zip


def unpack(archive_path: Path, processed_dir: Path) -> list[str]:
    """Extract only the expected files; refuse anything else (no path tricks, no extras)."""
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        unexpected = [name for name in names if not _MEMBER.match(name)]
        if unexpected:
            raise DemoDataError(f"Unexpected files in the demo archive: {unexpected}")
        required = {f"{EXTRACT_DIR}/manifest.json", PLAYER_SEASON_FILE}
        if missing := required - set(names):
            raise DemoDataError(f"The demo archive is missing {sorted(missing)}")
        for name in names:
            target = processed_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    return names


def ensure_demo_data(
    settings: Settings,
    *,
    env: dict[str, str] | None = None,
    fetch: Callable[[str], Iterable[bytes]] = _stream,
) -> bool:
    """Install the configured demo data if enabled and not already installed.

    A marker file records the checksum of the installed archive. When the configuration points
    to a new archive (a new release), the demo data is replaced on the next start; a server
    that keeps its files between updates would otherwise go on showing the old version. Data
    built locally (no marker) is never touched.

    Returns True when data was installed, False when nothing had to be done.
    """
    if not demo_enabled(env):
        return False
    source = settings.sources.demo_data
    if source is None:
        raise DemoDataError(f"{ENV_VAR} is set but sources.demo_data is not configured.")
    processed = settings.processed_dir
    marker = processed / MARKER_FILE
    has_data = (processed / EXTRACT_DIR / "manifest.json").exists()
    if has_data:
        if not marker.exists():
            return False  # built locally with the pipeline: never overwrite
        if marker.read_text(encoding="utf-8").strip() == source.sha256:
            return False  # this version is already installed
    archive = download(source.url, settings.raw_dir / source.filename, source.sha256, fetch=fetch)
    unpack(archive, processed)
    marker.write_text(source.sha256, encoding="utf-8")
    return True
