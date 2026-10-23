"""Smoke tests: every page runs end to end on a tiny invented dataset, in both languages."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from streamlit.testing.v1 import AppTest

from scouting.config import DEFAULT_CONFIG_PATH
from scouting.ingest import transfermarkt as tm
from scouting.ui.players import next_contract_deadline

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "pages").glob("*.py"))


@pytest.fixture
def app_env(source_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["scope"]["seasons"] = [2025]
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = config_dir / "settings.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    tm.extract(source_db, tmp_path / "data" / "processed" / "transfermarkt", ["PO1"], [2025])
    monkeypatch.setenv("SCOUTING_CONFIG", str(config))
    monkeypatch.chdir(ROOT)
    return config


def _run(page: str, lang: str = "en") -> AppTest:
    at = AppTest.from_file(str(ROOT / page), default_timeout=60)
    at.session_state["lang"] = lang
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("lang", ["en", "pt"])
def test_page_runs_without_errors(app_env: Path, page: str, lang: str) -> None:
    at = _run(page, lang)
    assert not at.exception, [e.value for e in at.exception]
    assert at.title, "every page has a title"


def test_router_runs(app_env: Path) -> None:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception


def test_missing_data_shows_readable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    (tmp_path / "config").mkdir()
    config = tmp_path / "config" / "settings.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setenv("SCOUTING_CONFIG", str(config))
    at = _run(PAGES[0])
    assert not at.exception
    assert any("fetch_data.py" in e.value for e in at.error)


@pytest.mark.parametrize(
    ("cutoff", "expected"),
    [("2026-05-24", "2027-06-30"), ("2026-07-06", "2027-06-30"), ("2025-12-01", "2026-06-30")],
)
def test_next_contract_deadline(cutoff: str, expected: str) -> None:
    assert next_contract_deadline(pd.Timestamp(cutoff)) == pd.Timestamp(expected)
