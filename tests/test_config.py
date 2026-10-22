from pathlib import Path

import pytest
import yaml

from scouting.config import DEFAULT_CONFIG_PATH, ConfigError, load_settings


def _write(tmp_path: Path, data: dict) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _base() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_default_settings_load() -> None:
    settings = load_settings()
    assert settings.scope.focus_competition == "PO1"
    assert "PO1" in settings.scope.competition_ids
    assert settings.scope.seasons == sorted(settings.scope.seasons)


def test_relative_paths_are_anchored_at_config_root(tmp_path: Path) -> None:
    settings = load_settings(_write(tmp_path, _base()))
    assert settings.raw_dir == tmp_path / "data" / "raw"
    assert settings.processed_dir == tmp_path / "data" / "processed"


def test_env_var_overrides_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _base()
    data["scope"]["seasons"] = [2025]
    monkeypatch.setenv("SCOUTING_CONFIG", str(_write(tmp_path, data)))
    assert load_settings().scope.seasons == [2025]


def test_seasons_are_deduplicated_and_sorted(tmp_path: Path) -> None:
    data = _base()
    data["scope"]["seasons"] = [2025, 2023, 2025]
    assert load_settings(_write(tmp_path, data)).scope.seasons == [2023, 2025]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["scope"].update(focus_competition="XX1"), "focus_competition"),
        (lambda d: d["scope"].update(seasons=[25]), "start years"),
        (lambda d: d["scope"].update(competitions={"po1": "x"}), "invalid competition codes"),
        (lambda d: d["sources"]["transfermarkt"].update(sha256="abc"), "sha256"),
        (lambda d: d.update(unknown_key=1), "unknown_key"),
    ],
)
def test_invalid_settings_raise_readable_errors(tmp_path: Path, mutate, message: str) -> None:
    data = _base()
    mutate(data)
    with pytest.raises(ConfigError, match=message):
        load_settings(_write(tmp_path, data))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "nope.yaml")
