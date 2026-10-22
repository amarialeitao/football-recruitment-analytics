"""Data-quality and status-board tests. All data is invented."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from scouting.config import Analysis, Quality
from scouting.health import status_board
from scouting.ingest import transfermarkt as tm
from scouting.quality import (
    KEY_FIELDS,
    coverage,
    field_completeness,
    future_transfers,
    stale_value_share,
    summarize,
)
from scouting.transform.player_season import build_player_season
from scouting.transform.tables import load_tables

TODAY = pd.Timestamp("2026-10-22")


@pytest.fixture
def built(source_db: Path, tmp_path: Path):
    out = tmp_path / "extract"
    tm.extract(source_db, out, ["PO1"], [2025])
    tables = load_tables(out)
    return tables, build_player_season(tables)


def test_coverage_counts_games_and_players(built) -> None:
    tables, ps = built
    cov = coverage(tables, ps, min_minutes=60)
    row = cov.iloc[0]
    assert (row["competition_id"], row["season"], row["games"]) == ("PO1", 2025, 1)
    assert row["players"] == 2
    assert row["players_min_minutes"] == 2


def test_field_completeness_only_key_fields() -> None:
    df = pd.DataFrame({"date_of_birth": [1, None], "foot": ["l", "r"], "other": [None, None]})
    out = field_completeness(df)
    assert out == {"date_of_birth": 0.5, "foot": 1.0}
    assert set(out) <= set(KEY_FIELDS)


def test_stale_value_share() -> None:
    df = pd.DataFrame(
        {
            "season": [2025, 2025, 2025, 2025],
            "minutes": [1000, 1000, 1000, 100],
            "market_value_end_date": pd.to_datetime(
                ["2026-05-01", "2024-01-01", None, "2020-01-01"]
            ),
        }
    )
    assert stale_value_share(df, min_minutes=900) == pytest.approx(2 / 3)


def test_future_transfers_use_today(built) -> None:
    tables, _ = built
    assert len(future_transfers(tables, pd.Timestamp("2025-01-01"))) == 0
    assert len(future_transfers(tables, pd.Timestamp("2024-01-01"))) == 1


def test_summarize(built) -> None:
    tables, ps = built
    s = summarize(tables, ps, min_minutes=60, today=TODAY)
    assert s.games == 1
    # The fixture game ends 2-1 but lists a single goal event: it must be flagged.
    assert s.unreconciled_games == 1
    assert s.duplicate_keys == 0
    assert s.player_seasons == len(ps)
    assert s.data_cutoff == pd.Timestamp("2025-09-01")
    assert 0 <= s.completeness_min[1] <= 1


# --- status board ------------------------------------------------------------------------------


@pytest.fixture
def summary(built):
    tables, ps = built
    return summarize(tables, ps.assign(comparison_n=150), min_minutes=60, today=TODAY)


def _status(items, area: str) -> str:
    return next(i.status for i in items if i.area["en"] == area)


def test_board_has_fixed_areas_with_bilingual_reasons(summary) -> None:
    items = status_board(summary, quality=Quality(), analysis=Analysis(), today=TODAY)
    assert [i.area["en"] for i in items] == [
        "Data freshness",
        "Profile completeness",
        "Match events",
        "Market values",
        "Comparison groups",
    ]
    for item in items:
        assert item.status in {"ok", "attention"}
        assert item.reason["en"] and item.reason["pt"]


def test_freshness_follows_configured_age(summary) -> None:
    old = status_board(summary, quality=Quality(), analysis=Analysis(), today=TODAY)
    assert _status(old, "Data freshness") == "attention"
    recent = status_board(
        summary, quality=Quality(), analysis=Analysis(), today=pd.Timestamp("2025-10-01")
    )
    assert _status(recent, "Data freshness") == "ok"


def test_thresholds_come_from_config(summary) -> None:
    strict = Quality(completeness_min=1.0, max_stale_value_share=0.0)
    lenient = Quality(completeness_min=0.0, max_stale_value_share=1.0)
    bad = replace(summary, stale_value_share=0.5, completeness={"foot": 0.5})
    assert (
        _status(
            status_board(bad, quality=strict, analysis=Analysis(), today=TODAY), "Market values"
        )
        == "attention"
    )
    assert (
        _status(
            status_board(bad, quality=lenient, analysis=Analysis(), today=TODAY), "Market values"
        )
        == "ok"
    )
    assert (
        _status(
            status_board(bad, quality=strict, analysis=Analysis(), today=TODAY),
            "Profile completeness",
        )
        == "attention"
    )


def test_events_and_duplicates_raise_attention(summary) -> None:
    broken = replace(summary, unreconciled_games=1, games=10)
    assert (
        _status(
            status_board(broken, quality=Quality(), analysis=Analysis(), today=TODAY),
            "Match events",
        )
        == "attention"
    )
    dupes = replace(summary, duplicate_keys=2)
    assert (
        _status(
            status_board(dupes, quality=Quality(), analysis=Analysis(), today=TODAY), "Match events"
        )
        == "attention"
    )


def test_small_comparison_groups_raise_attention(summary) -> None:
    small = replace(summary, smallest_comparison_group=20)
    assert (
        _status(
            status_board(small, quality=Quality(), analysis=Analysis(), today=TODAY),
            "Comparison groups",
        )
        == "attention"
    )
    none = replace(summary, smallest_comparison_group=None)
    items = status_board(none, quality=Quality(), analysis=Analysis(), today=TODAY)
    assert _status(items, "Comparison groups") == "attention"


def test_completeness_reason_uses_readable_field_names(summary) -> None:
    worst = replace(summary, completeness={"market_value_end": 0.5, "foot": 0.9})
    items = status_board(worst, quality=Quality(), analysis=Analysis(), today=TODAY)
    item = next(i for i in items if i.area["en"] == "Profile completeness")
    assert "market value" in item.reason["en"] and "market_value_end" not in item.reason["en"]
    assert "valor de mercado" in item.reason["pt"]
