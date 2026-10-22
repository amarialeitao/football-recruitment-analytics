"""Tests for league strength. All values are invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting.metrics.league_strength import european_results, league_strength


def _games() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": [2025, 2025],
            "competition_id": ["AA1", "BB1"],
            "home_club_id": [1, 3],
            "away_club_id": [2, 4],
        }
    )


def _european() -> pd.DataFrame:
    # AA1 club 1 beats BB1 club 3; AA1 club 2 draws BB1 club 4; AA1 club 1 vs AA1 club 2 ignored.
    return pd.DataFrame(
        {
            "game_id": [1, 2, 3],
            "season": [2025, 2025, 2025],
            "home_club_id": [1, 4, 1],
            "away_club_id": [3, 2, 2],
            "home_club_goals": [2, 1, 0],
            "away_club_goals": [0, 1, 0],
        }
    )


def _clubs() -> pd.DataFrame:
    return pd.DataFrame(
        {"club_id": [1, 2, 3, 4], "domestic_competition_id": ["AA1"] * 2 + ["BB1"] * 2}
    )


def test_european_results_only_count_games_between_leagues() -> None:
    res = european_results(_european(), _games(), _clubs()).set_index("competition_id")
    assert res.loc["AA1", "european_games"] == 2
    assert res.loc["AA1", "european_ppg"] == pytest.approx(2.0)  # win + draw
    assert res.loc["BB1", "european_ppg"] == pytest.approx(0.5)  # loss + draw
    assert res.loc["AA1", "european_goal_diff_pg"] == pytest.approx(1.0)


def test_european_results_use_season_league_before_current_league() -> None:
    clubs = _clubs()
    clubs.loc[clubs["club_id"] == 3, "domestic_competition_id"] = "AA1"  # since promoted/moved
    res = european_results(_european(), _games(), clubs).set_index("competition_id")
    assert res.loc["BB1", "european_games"] == 2


def test_league_strength_index_is_relative_to_focus(ps: pd.DataFrame) -> None:
    out = league_strength(ps, _european(), _games(), _clubs(), focus_competition="AA1")
    out = out.set_index("competition_id")
    assert out.loc["AA1", "strength_index"] == pytest.approx(100.0)
    assert out.loc["BB1", "strength_index"] < 100  # AA1 values are 1.5x in the synthetic data
    assert out.loc["BB1", "european_games"] == 2
