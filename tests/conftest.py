"""Shared fixtures. All data here is invented and only mirrors the source schema."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from metric_data import synthetic_player_season

SCHEMA = [
    """create table competitions(competition_id varchar, name varchar, type varchar,
        country_name varchar)""",
    "create table clubs(club_id integer, name varchar, domestic_competition_id varchar)",
    """create table games(game_id integer, competition_id varchar, season varchar, date date,
        home_club_id integer, away_club_id integer, home_club_goals integer,
        away_club_goals integer)""",
    """create table appearances(appearance_id varchar, game_id varchar, player_id integer,
        player_club_id integer, competition_id varchar, minutes_played integer, goals integer,
        assists integer, yellow_cards integer, red_cards integer)""",
    """create table game_events(game_id varchar, minute integer, type varchar, club_id integer,
        player_id integer, player_in_id integer)""",
    """create table game_lineups(game_id integer, player_id integer, club_id integer, type varchar,
        position varchar)""",
    """create table players(player_id integer, name varchar, date_of_birth date, position varchar,
        sub_position varchar, foot varchar, height_in_cm integer, country_of_citizenship varchar,
        current_club_id integer, contract_expiration_date date, market_value_in_eur double)""",
    "create table player_valuations(player_id integer, date date, market_value_in_eur double)",
    """create table transfers(player_id varchar, transfer_date date, from_club_id integer,
        to_club_id integer, transfer_fee double)""",
    "create table version(version varchar, published_at date)",
]

ROWS = [
    """insert into competitions values
        ('PO1', 'league-a', 'domestic_league', 'Country A'),
        ('ES1', 'league-b', 'domestic_league', 'Country B'),
        ('XX1', 'league-out', 'domestic_league', 'Country X'),
        ('CL', 'euro-cup', 'international_cup', null)""",
    """insert into clubs values
        (1, 'Club One', 'PO1'), (2, 'Club Two', 'PO1'), (3, 'Club Three', 'XX1')""",
    """insert into games values
        (100, 'PO1', '2025', '2025-09-01', 1, 2, 2, 1),
        (101, 'PO1', '2020', '2020-09-01', 1, 2, 0, 0),
        (102, 'XX1', '2025', '2025-09-02', 3, 3, 1, 1),
        (103, 'CL', '2025', '2025-10-01', 1, 3, 1, 0),
        (104, 'CL', '2019', '2019-10-01', 1, 3, 1, 0)""",
    """insert into appearances values
        ('100_10', 100, 10, 1, 'PO1', 90, 1, 0, 0, 0),
        ('100_11', 100, 11, 2, 'PO1', 60, 0, 1, 1, 0),
        ('101_10', 101, 10, 1, 'PO1', 90, 0, 0, 0, 0),
        ('102_12', 102, 12, 3, 'XX1', 90, 1, 0, 0, 0)""",
    """insert into game_events values
        (100, 60, 'Substitutions', 2, 11, 13), (100, 30, 'Goals', 1, 10, null),
        (102, 10, 'Goals', 3, 12, null)""",
    """insert into game_lineups values
        (100, 10, 1, 'starting_lineup', 'Centre-Forward'),
        (100, 11, 2, 'starting_lineup', 'Left-Back'),
        (102, 12, 3, 'starting_lineup', 'Goalkeeper')""",
    """insert into players values
        (10, 'Player Ten', '2000-01-01', 'Attack', 'Centre-Forward', 'right', 182, 'Country A', 1,
         '2027-06-30', 1500000),
        (11, 'Player Eleven', '2003-05-05', 'Defender', 'Left-Back', 'left', 175, 'Country B', 2,
         null, 400000),
        (12, 'Player Twelve', '1995-02-02', 'Goalkeeper', 'Goalkeeper', 'right', 190, 'Country X',
         3, '2026-06-30', 900000)""",
    """insert into player_valuations values
        (10, '2025-06-01', 1000000), (10, '2026-01-01', 1500000), (12, '2026-01-01', 900000)""",
    """insert into transfers values
        (10, '2024-07-01', 3, 1, 500000), (12, '2023-07-01', 1, 3, 0)""",
    "insert into version values ('2026-07-06', '2026-07-06')",
]


def make_source_db(path: Path, *, drop_column: tuple[str, str] | None = None) -> Path:
    """Create a small DuckDB file shaped like transfermarkt-datasets."""
    con = duckdb.connect(str(path))
    try:
        for statement in SCHEMA + ROWS:
            con.execute(statement)
        if drop_column:
            table, column = drop_column
            con.execute(f"alter table {table} drop column {column}")
    finally:
        con.close()
    return path


@pytest.fixture
def source_db(tmp_path: Path) -> Path:
    return make_source_db(tmp_path / "source.duckdb")


@pytest.fixture
def ps() -> pd.DataFrame:
    """Synthetic player-season table (see tests/metric_data.py)."""
    return synthetic_player_season()
