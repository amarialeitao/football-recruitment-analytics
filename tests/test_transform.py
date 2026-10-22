"""Transform tests on small, hand-made frames. All names and numbers are invented."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scouting.ingest import transfermarkt as tm
from scouting.transform.player_season import build_player_season, season_label
from scouting.transform.stints import build_stints, reconcile_goal_events
from scouting.transform.tables import Tables, load_tables, normalize, normalize_frame

# Club 1 (home) beats club 2 (away) 2-1 in game 1. Club 1 also plays game 2 (1-1) vs club 3.
# Player 10: club 1, starts game 1, subbed off at 60. Starts game 2, plays 90.
# Player 11: club 1, comes on at 60 in game 1.
# Player 12: club 2, starts game 1, plays 90.
# Player 13: club 1 in game 1 bench (unused, 0 minutes).
# Player 14: club 3, starts game 2; there is no substitution event for player 15.
# Player 15: club 3, on the bench in game 2, played 20 minutes (fallback start = 70).
# Game 1 goals: club 1 at 30 (by 10), club 2 at 70 (own goal by player 11 -> credited to club 2),
#               club 1 at 80 (by 11).
# Game 2 events only list one goal although the score is 1-1 -> not reconciled.


def raw_frames() -> dict[str, pd.DataFrame]:
    games = pd.DataFrame(
        {
            "game_id": ["1", "2"],
            "competition_id": ["AA1", "AA1"],
            "season": ["2025", "2025"],
            "date": ["2025-09-01", "2025-09-08"],
            "home_club_id": [1, 1],
            "away_club_id": [2, 3],
            "home_club_goals": [2, 1],
            "away_club_goals": [1, 1],
        }
    )
    appearances = pd.DataFrame(
        {
            "appearance_id": ["1_10", "1_11", "1_12", "1_13", "2_10", "2_14", "2_15"],
            "game_id": [1, 1, 1, 1, 2, 2, 2],
            "player_id": [10, 11, 12, 13, 10, 14, 15],
            "player_club_id": [1, 1, 2, 1, 1, 3, 3],
            "competition_id": ["AA1"] * 7,
            "minutes_played": [60, 30, 90, 0, 90, 90, 20],
            "goals": [1, 1, 0, 0, 0, 1, 0],
            "assists": [0, 0, 0, 0, 1, 0, 0],
            "yellow_cards": [0, 1, 0, 0, 0, 0, 0],
            "red_cards": [0, 0, 0, 0, 0, 0, 0],
        }
    )
    lineups = pd.DataFrame(
        {
            "game_id": [1, 1, 1, 1, 2, 2, 2],
            "player_id": [10, 11, 12, 13, 10, 14, 15],
            "club_id": [1, 1, 2, 1, 1, 3, 3],
            "type": [
                "starting_lineup",
                "substitutes",
                "starting_lineup",
                "substitutes",
                "starting_lineup",
                "starting_lineup",
                "substitutes",
            ],
            "position": [
                "Centre-Forward",
                "Left Winger",
                "Goalkeeper",
                "Centre-Back",
                "Left Winger",
                "Centre-Back",
                "Right-Back",
            ],
        }
    )
    events = pd.DataFrame(
        {
            "game_id": ["1", "1", "1", "1", "2"],
            "minute": [30, 60, 70, 80, 50],
            "type": ["Goals", "Substitutions", "Goals", "Goals", "Goals"],
            "club_id": [1, 1, 2, 1, 3],
            "player_id": [10, 10, 11, 11, 14],
            "player_in_id": [None, 11, None, None, None],
        }
    )
    players = pd.DataFrame(
        {
            "player_id": [10, 11, 12, 13, 14, 15],
            "name": ["P10", "P11", "P12", "P13", "P14", "P15"],
            "date_of_birth": pd.to_datetime(
                ["2000-01-01", "2004-07-01", "1996-01-01", "2001-01-01", "1999-01-01", "2003-01-01"]
            ).as_unit("s"),
            "position": ["Attack", "Attack", "Goalkeeper", "Defender", "Defender", "Defender"],
            "sub_position": [
                "Centre-Forward",
                "Left Winger",
                "Goalkeeper",
                "Centre-Back",
                "Centre-Back",
                "Right-Back",
            ],
            "foot": ["right"] * 6,
            "height_in_cm": [180] * 6,
            "country_of_citizenship": ["Country A"] * 6,
            "contract_expiration_date": pd.to_datetime(["2027-06-30"] * 6),
            "current_club_id": ["1", "1", "2", "1", "3", "3"],
        }
    )
    valuations = pd.DataFrame(
        {
            "player_id": [10, 10, 10, 11],
            "date": pd.to_datetime(
                ["2025-01-01", "2025-12-01", "2026-08-01", "2026-03-01"]
            ).as_unit("us"),
            "market_value_in_eur": [1_000_000, 2_000_000, 9_000_000, 500_000],
        }
    )
    clubs = pd.DataFrame(
        {"club_id": ["1", "2", "3"], "name": ["Club One", "Club Two", "Club Three"]}
    )
    empty = pd.DataFrame()
    return {
        "competitions": pd.DataFrame({"competition_id": ["AA1"]}),
        "clubs": clubs,
        "games": games,
        "european_games": empty,
        "appearances": appearances,
        "game_events": events,
        "game_lineups": lineups,
        "players": players,
        "player_valuations": valuations,
        "transfers": pd.DataFrame({"player_id": [10], "transfer_date": ["2024-07-01"]}),
    }


@pytest.fixture
def tables() -> Tables:
    return normalize(raw_frames())


@pytest.fixture
def stints(tables: Tables) -> pd.DataFrame:
    return build_stints(tables.games, tables.appearances, tables.game_lineups, tables.game_events)


def _row(df: pd.DataFrame, **match) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for column, value in match.items():
        mask &= df[column] == value
    rows = df[mask]
    assert len(rows) == 1, f"expected one row for {match}, got {len(rows)}"
    return rows.iloc[0]


# --- normalize ---------------------------------------------------------------------------------


def test_normalize_unifies_id_types_across_tables(tables: Tables) -> None:
    assert str(tables.games["game_id"].dtype) == "Int64"
    assert str(tables.game_events["game_id"].dtype) == "Int64"
    assert str(tables.appearances["game_id"].dtype) == "Int64"
    assert str(tables.clubs["club_id"].dtype) == "Int64"


def test_normalize_seasons_and_dates(tables: Tables) -> None:
    assert tables.games["season"].tolist() == [2025, 2025]
    assert str(tables.players["date_of_birth"].dtype) == "datetime64[ns]"
    assert str(tables.player_valuations["date"].dtype) == "datetime64[ns]"


def test_normalize_frame_coerces_bad_values_to_missing() -> None:
    out = normalize_frame(pd.DataFrame({"player_id": ["7", "x"], "date": ["2025-01-01", "bad"]}))
    assert out["player_id"].isna().tolist() == [False, True]
    assert out["date"].isna().tolist() == [False, True]


def test_normalize_requires_all_tables() -> None:
    frames = raw_frames()
    del frames["players"]
    with pytest.raises(KeyError, match="players"):
        normalize(frames)


# --- stints ------------------------------------------------------------------------------------


def test_reconcile_goal_events(tables: Tables) -> None:
    ok = reconcile_goal_events(tables.games, tables.game_events)
    assert ok.to_dict() == {1: True, 2: False}


def test_unused_substitutes_have_no_stint(stints: pd.DataFrame) -> None:
    assert 13 not in stints["player_id"].tolist()


def test_stint_bounds(stints: pd.DataFrame) -> None:
    starter = _row(stints, game_id=1, player_id=10)
    assert (starter["start"], starter["end"], starter["started"]) == (0, 60, True)
    sub = _row(stints, game_id=1, player_id=11)
    assert (sub["start"], sub["end"], sub["started"]) == (60, 90, False)


def test_stint_falls_back_when_substitution_event_missing(stints: pd.DataFrame) -> None:
    sub = _row(stints, game_id=2, player_id=15)
    assert (sub["start"], sub["end"]) == (70, 90)


def test_on_pitch_goals_respect_interval_and_own_goals(stints: pd.DataFrame) -> None:
    starter = _row(stints, game_id=1, player_id=10)  # on 0-60: only the goal at 30
    assert (starter["goals_for_on"], starter["goals_against_on"]) == (1, 0)
    sub = _row(stints, game_id=1, player_id=11)  # on 60-90: own goal at 70 against, goal at 80
    assert (sub["goals_for_on"], sub["goals_against_on"]) == (1, 1)
    keeper = _row(stints, game_id=1, player_id=12)  # club 2, full game
    assert (keeper["goals_for_on"], keeper["goals_against_on"]) == (1, 2)


def test_unreconciled_game_leaves_on_pitch_goals_empty(stints: pd.DataFrame) -> None:
    row = _row(stints, game_id=2, player_id=14)
    assert not row["events_reconciled"]
    assert pd.isna(row["goals_for_on"]) and pd.isna(row["goals_against_on"])


# --- player season -----------------------------------------------------------------------------


@pytest.fixture
def season(tables: Tables, stints: pd.DataFrame) -> pd.DataFrame:
    return build_player_season(tables, stints)


def test_one_row_per_player_season_competition(season: pd.DataFrame) -> None:
    assert not season.duplicated(["player_id", "season", "competition_id"]).any()
    assert sorted(season["player_id"]) == [10, 11, 12, 14, 15]


def test_usage_and_per90(season: pd.DataFrame) -> None:
    p10 = _row(season, player_id=10)
    assert (p10["games"], p10["starts"], p10["minutes"]) == (2, 2, 150)
    assert (p10["goals"], p10["assists"], p10["goal_contributions"]) == (1, 1, 2)
    assert p10["goal_contributions_p90"] == pytest.approx(2 * 90 / 150)
    assert p10["team_games"] == 2
    assert p10["minutes_share"] == pytest.approx(150 / 180)
    assert p10["start_rate"] == 1.0


def test_on_pitch_per90_uses_only_reconciled_minutes(season: pd.DataFrame) -> None:
    p10 = _row(season, player_id=10)
    assert p10["reconciled_minutes"] == 60
    assert p10["plus_minus_on"] == 1
    assert p10["plus_minus_on_p90"] == pytest.approx(1 * 90 / 60)
    p14 = _row(season, player_id=14)
    assert p14["reconciled_minutes"] == 0
    assert pd.isna(p14["plus_minus_on_p90"])


def test_profile_fields(season: pd.DataFrame) -> None:
    p10 = _row(season, player_id=10)
    assert p10["age"] == pytest.approx(26.0, abs=0.1)
    assert p10["position_group"] == "Forward"
    assert p10["main_lineup_position"] in {"Centre-Forward", "Left Winger"}
    assert p10["n_lineup_positions"] == 2
    assert p10["club_name"] == "Club One"
    assert p10["season_label"] == "2025/26"


def test_market_value_at_season_start_and_end(season: pd.DataFrame) -> None:
    p10 = _row(season, player_id=10)
    assert p10["market_value_start"] == 1_000_000  # last value on or before 2025-07-01
    assert p10["market_value_end"] == 2_000_000  # last value on or before 2026-06-30
    assert p10["market_value_change"] == 1_000_000
    p11 = _row(season, player_id=11)
    assert pd.isna(p11["market_value_start"])
    assert p11["market_value_end"] == 500_000


def test_main_club_when_player_moves_within_league(tables: Tables) -> None:
    frames = raw_frames()
    frames["appearances"].loc[
        frames["appearances"]["appearance_id"] == "2_10", "player_club_id"
    ] = 3
    frames["game_lineups"].loc[
        (frames["game_lineups"]["game_id"] == 2) & (frames["game_lineups"]["player_id"] == 10),
        "club_id",
    ] = 3
    moved = normalize(frames)
    row = _row(build_player_season(moved), player_id=10)
    assert row["n_clubs"] == 2
    assert row["club_id"] == 3  # 90 minutes at club 3 vs 60 at club 1


def test_season_label() -> None:
    assert season_label(2025) == "2025/26"
    assert season_label(2099) == "2099/00"


# --- integration with the ingest step ----------------------------------------------------------


def test_extract_then_transform_end_to_end(source_db: Path, tmp_path: Path) -> None:
    out = tmp_path / "extract"
    tm.extract(source_db, out, ["PO1"], [2025])
    tables = load_tables(out)
    table = build_player_season(tables)
    assert set(table["player_id"]) == {10, 11}
    assert set(table["competition_id"]) == {"PO1"}
    assert (table["minutes"] > 0).all()


def test_load_tables_reports_missing_extract(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="fetch_data.py"):
        load_tables(tmp_path)
