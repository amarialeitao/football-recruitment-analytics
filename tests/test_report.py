"""One-page player report. Synthetic rows: all names and numbers are invented."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from scouting.insights import Insight
from scouting.metrics.catalog import PROFILE_METRICS
from scouting.report import ReportInput, player_report_html, report_filename

KEYS = list(PROFILE_METRICS["Forward"])


def _row(**overrides) -> pd.Series:
    data = {
        "name": "Jo <b>Silva</b>",
        "season": 2025,
        "position_group": "Forward",
        "sub_position": "Centre-Forward",
        "club_name": "Club A",
        "competition_name": "League A",
        "age": 22.4,
        "minutes": 2100,
        "minutes_share": 0.71,
        "market_value_start": 400_000.0,
        "market_value_end": 1_250_000.0,
        "expected_market_value": 2_500_000.0,
        "value_ratio": 0.5,
        "contract_expiration_date": pd.Timestamp("2028-06-30"),
        "comparison_n": 490,
    }
    for i, key in enumerate(KEYS):
        data.setdefault(key, 0.1 * (i + 1))  # keep the real minutes_share defined above
        data[f"{key}_pct"] = 10.0 * (i + 2)
    data.update(overrides)
    return pd.Series(data)


def _input(row: pd.Series, **overrides) -> ReportInput:
    params = {
        "row": row,
        "profile_keys": KEYS,
        "insights": [Insight("strength:x", {"en": "Top 5% for goals.", "pt": "Top 5%."}, "high")],
        "min_minutes": 900,
        "confidence": "high",
        "data_cutoff": pd.Timestamp("2026-05-24"),
        "season_label": "2025/26",
        "strength_index": 32.0,
        "trend_insights": [
            Insight("trend:00:x", {"en": "Start rate: improved.", "pt": "Melhorou."}, "medium")
        ],
        "previous_season_label": "2024/25",
    }
    params.update(overrides)
    return ReportInput(**params)


def test_report_is_self_contained_and_escaped() -> None:
    page = player_report_html(_input(_row()), "en")
    assert page.startswith("<!doctype html>")
    assert "<b>Silva</b>" not in page and "Jo &lt;b&gt;Silva&lt;/b&gt;" in page
    assert not re.search(r"(src|href)=", page)  # no external files, opens offline
    assert "@page" in page  # print layout


def test_report_content_in_english() -> None:
    page = player_report_html(_input(_row()), "en")
    for text in (
        "Scouting report",
        "Centre-Forward · Club A (League A) · 2025/26",
        "2,100",
        "71% of his team&#x27;s",  # apostrophe is escaped in the HTML
        "€1.2m",  # market value, rounded like the app
        "0.50x",
        "2028-06-30",
        "490 forwards with 900+ minutes",
        "Change since 2024/25",
        "Start rate: improved.",
        "Top 5% for goals.",
        "high confidence",
        "Expected goals (xG)",
        "league games to 2026-05-24",
        "not affiliated with any club",
    ):
        assert text in page, text
    assert page.count('class="bar-row"') == len(KEYS)


def test_report_in_portuguese_uses_local_formats() -> None:
    page = player_report_html(_input(_row()), "pt")
    assert 'lang="pt"' in page
    assert "Relatório de scouting" in page
    assert "Ponta de lança" in page
    assert "2.100" in page and "0,50x" in page
    assert "Evolução desde 2024/25" in page


def test_low_minutes_and_missing_fields_are_explained_not_invented() -> None:
    row = _row(minutes=400, value_ratio=float("nan"), contract_expiration_date=pd.NaT)
    page = player_report_html(
        _input(
            row,
            profile_keys=[],
            trend_insights=[],
            trend_note="No previous season in the leagues in scope.",
            previous_season_label=None,
            strength_index=None,
        ),
        "en",
    )
    assert 'class="bar-row"' not in page
    assert "Fewer than 900 minutes" in page
    assert "Value vs expected" not in page
    assert "not in the data" in page
    assert "League level" not in page
    assert "Change since last season" in page and "No previous season" in page


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Güven Yalçın", "report_guven-yalcin_2025-26.html"),
        ("Pierre Landry Kaboré", "report_pierre-landry-kabore_2025-26.html"),
        ("Søren Østergaard", "report_soren-ostergaard_2025-26.html"),
        ("", "report_player_2025-26.html"),
    ],
)
def test_report_filename_is_safe(name: str, expected: str) -> None:
    assert report_filename(pd.Series({"name": name}), "2025/26") == expected
