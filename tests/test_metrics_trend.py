"""Season-over-season change. Hand-made rows: all names and numbers are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting.metrics import trend

KEYS = ["start_rate", "minutes_share", "goal_contributions_p90", "yellow_cards_p90"]


def _row(season: int, minutes: int, pcts: dict[str, float], **extra) -> dict:
    out = {"player_id": 7, "season": season, "minutes": minutes, **extra}
    out.update({f"{k}_pct": v for k, v in pcts.items()})
    return out


@pytest.fixture
def players() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row(
                2024,
                2000,
                {
                    "start_rate": 60,
                    "minutes_share": 70,
                    "goal_contributions_p90": 50,
                    "yellow_cards_p90": 40,
                },
                competition_id="AA1",
            ),
            _row(2024, 300, {}, competition_id="BB1"),  # loan spell: fewer minutes
            _row(
                2025,
                2900,
                {
                    "start_rate": 89,
                    "minutes_share": 75,
                    "goal_contributions_p90": 30,
                    "yellow_cards_p90": float("nan"),
                },
                competition_id="AA1",
            ),
            {"player_id": 8, "season": 2025, "minutes": 1500, "competition_id": "AA1"},
        ]
    )


def test_previous_season_prefers_most_minutes(players: pd.DataFrame) -> None:
    current = players.iloc[2]
    previous = trend.previous_season(players, current)
    assert previous is not None
    assert previous["competition_id"] == "AA1" and previous["minutes"] == 2000
    assert trend.previous_season(players, players.iloc[3]) is None


def test_changes_directions_order_and_missing_metrics(players: pd.DataFrame) -> None:
    current, previous = players.iloc[2], players.iloc[0]
    changes = trend.season_changes(current, previous, KEYS, threshold=10)
    # yellow cards has no percentile this season: left out rather than guessed
    assert list(changes["metric"]) == ["start_rate", "goal_contributions_p90", "minutes_share"]
    assert list(changes["direction"]) == ["up", "down", "same"]
    assert changes.loc[0, "change"] == pytest.approx(29)


def test_threshold_is_inclusive(players: pd.DataFrame) -> None:
    current, previous = players.iloc[2], players.iloc[0]
    changes = trend.season_changes(current, previous, ["minutes_share"], threshold=5)
    assert changes.loc[0, "direction"] == "up"  # +5 with threshold 5


def test_insights_in_both_languages_with_weakest_confidence(players: pd.DataFrame) -> None:
    current, previous = players.iloc[2], players.iloc[0]
    changes = trend.season_changes(current, previous, KEYS, threshold=10)
    insights = trend.change_insights(
        changes, current=current, previous=previous, confidence_minutes=(900, 2500)
    )
    texts = [i.text["en"] for i in insights]
    assert texts[0] == "Start rate: improved, percentile 60 → 89."
    assert texts[1] == "Goals + assists per 90: declined, percentile 50 → 30."
    assert texts[2] == "About the same as last season: share of team minutes."
    assert insights[0].text["pt"].endswith("melhorou, percentil 60 → 89.")
    # Sorting by the page keeps biggest change first and "about the same" last.
    from scouting.insights import sort_insights

    assert [i.key for i in sort_insights(insights)] == [i.key for i in insights]
    # 2,000 minutes last season is below the 2,500 'high' bar: medium, not high
    assert {i.confidence for i in insights} == {"medium"}
    assert all(i.kind == "observation" for i in insights)


def test_minutes_note_explains_missing_comparison(players: pd.DataFrame) -> None:
    assert "No previous season" in trend.minutes_note(None, 900, "en")
    loan = players.iloc[1]
    assert "300" in trend.minutes_note(loan, 900, "en")
    assert "época anterior" in trend.minutes_note(loan, 900, "pt")
    assert trend.minutes_note(players.iloc[0], 900, "en") is None


def test_chart_draws_one_line_per_metric(players: pd.DataFrame) -> None:
    from scouting.ui import charts

    current, previous = players.iloc[2], players.iloc[0]
    changes = trend.season_changes(current, previous, KEYS, threshold=10)
    fig = charts.season_change(changes, "en", title="T", seasons=("2024/25", "2025/26"))
    lines = [tr for tr in fig.data if tr.mode == "lines"]
    assert len(lines) == len(changes)
    assert [tr.name for tr in fig.data if tr.mode != "lines"] == ["2024/25", "2025/26"]
    assert "100 = best" in fig.layout.xaxis.title.text
