"""Data checks on a table built by the real pipeline from the synthetic source. Data is invented."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from scouting.checks import DataCheckError, assert_valid, errors, report, run_checks, warnings
from scouting.config import DEFAULT_CONFIG_PATH, Checks, load_settings
from scouting.ingest import transfermarkt as tm
from scouting.transform.player_season import build_player_season
from scouting.transform.tables import load_tables

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def table(source_db: Path, tmp_path: Path) -> pd.DataFrame:
    out = tm.extract(source_db, tmp_path / "extract", ["PO1"], [2025]).out_dir
    return build_player_season(load_tables(out))


@pytest.fixture
def settings():
    return load_settings()


def _failing(results, name: str) -> int:
    return next(r for r in results if r.name == name).failing


def test_pipeline_output_passes_every_error_rule(table: pd.DataFrame, settings) -> None:
    results = run_checks(table, settings)
    assert errors(results) == []
    assert_valid(results)  # does not raise
    assert "One row per player, season and league" in report(results)


@pytest.mark.parametrize(
    ("name", "breaks"),
    [
        ("unique_rows", lambda df: pd.concat([df, df.head(1)], ignore_index=True)),
        ("ids_present", lambda df: df.assign(club_id=pd.Series([pd.NA] * len(df), dtype="Int64"))),
        ("in_scope", lambda df: df.assign(competition_id="XX1")),
        ("minutes_range", lambda df: df.assign(minutes=-5)),
        ("minutes_range", lambda df: df.assign(minutes=df["games"] * 90 + 1)),
        ("starts_le_games", lambda df: df.assign(starts=df["games"] + 1)),
        ("games_le_team_games", lambda df: df.assign(n_clubs=1, games=df["team_games"] + 1)),
        ("shares_0_1", lambda df: df.assign(minutes_share=1.2)),
        ("counts_non_negative", lambda df: df.assign(goals=-1)),
        ("on_pitch_goals", lambda df: df.assign(plus_minus_on=df["plus_minus_on"] + 1)),
        ("age_plausible", lambda df: df.assign(age=9.0)),
        ("market_value_plausible", lambda df: df.assign(market_value_end=0.0)),
        ("market_value_plausible", lambda df: df.assign(market_value_end=5e8)),
    ],
)
def test_each_error_rule_catches_its_problem(table, settings, name, breaks) -> None:
    results = run_checks(breaks(table.copy()), settings)
    assert _failing(results, name) > 0
    with pytest.raises(DataCheckError, match=name):
        assert_valid(results)


def test_mover_may_play_more_games_than_main_club(table, settings) -> None:
    moved = table.assign(n_clubs=2, games=table["team_games"] + 1, starts=0)
    moved["minutes"] = moved["games"] * 10
    assert _failing(run_checks(moved, settings), "games_le_team_games") == 0


def test_warnings_never_block(table, settings) -> None:
    odd = table.copy()
    odd.loc[odd.index[0], "height_in_cm"] = 19
    odd.loc[odd.index[0], "contract_expiration_date"] = pd.Timestamp("2000-05-31")
    odd.loc[odd.index[0], "position_group"] = None
    results = run_checks(odd, settings)
    assert {r.name for r in warnings(results)} == {
        "height_plausible",
        "contract_not_expired",
        "position_known",
    }
    assert_valid(results)  # warnings only: does not raise
    example = next(r for r in results if r.name == "height_plausible").examples[0]
    assert set(example) == {"name", "season", "competition_id"}


def test_missing_values_are_not_failures(table, settings) -> None:
    blank = table.assign(age=float("nan"), market_value_end=float("nan"), height_in_cm=pd.NA)
    results = run_checks(blank, settings)
    for name in ("age_plausible", "market_value_plausible", "height_plausible"):
        assert _failing(results, name) == 0


def test_bounds_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        Checks(age_range=(45, 14))


def test_build_dataset_refuses_a_broken_table(
    source_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["checks"]["age_range"] = [40, 45]  # every synthetic player is younger: errors
    config = tmp_path / "config" / "settings.yaml"
    config.parent.mkdir()
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    tm.extract(source_db, tmp_path / "data" / "processed" / "transfermarkt", ["PO1"], [2025])

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import build_dataset

    assert build_dataset.main(["--config", str(config)]) == 1
    assert "Not written" in capsys.readouterr().out
    assert not (tmp_path / "data" / "processed" / "player_season.parquet").exists()

    data["checks"]["age_range"] = [14, 45]
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert build_dataset.main(["--config", str(config)]) == 0
    assert (tmp_path / "data" / "processed" / "player_season.parquet").exists()
