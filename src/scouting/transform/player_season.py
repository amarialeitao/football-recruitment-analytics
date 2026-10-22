"""The central analysis table: one row per player, season and competition.

Grain: ``(player_id, season, competition_id)``. A player who changed clubs within the same league
in one season gets one row; ``club_id`` is the club where he played most minutes and
``n_clubs`` says how many clubs he played for. Per-90 metrics use official minutes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scouting.transform.stints import MATCH_MINUTES, build_stints
from scouting.transform.tables import DATE_DTYPE, Tables

KEY = ["player_id", "season", "competition_id"]

PER90_SOURCES = {
    "goals": "goals_p90",
    "assists": "assists_p90",
    "goal_contributions": "goal_contributions_p90",
    "yellow_cards": "yellow_cards_p90",
    "red_cards": "red_cards_p90",
    "goals_for_on": "goals_for_on_p90",
    "goals_against_on": "goals_against_on_p90",
    "plus_minus_on": "plus_minus_on_p90",
}

POSITION_GROUPS = {
    "Goalkeeper": "Goalkeeper",
    "Defender": "Defender",
    "Midfield": "Midfielder",
    "Attack": "Forward",
}


def season_label(season: int) -> str:
    """2025 -> '2025/26'."""
    return f"{season}/{(season + 1) % 100:02d}"


def _per90(numerator: pd.Series, minutes: pd.Series) -> pd.Series:
    return (numerator * MATCH_MINUTES / minutes.where(minutes > 0)).astype("Float64")


def _value_on_or_before(
    keys: pd.DataFrame, valuations: pd.DataFrame, date_column: str, name: str
) -> pd.DataFrame:
    """Latest market value per ``player_id`` on or before each row's ``date_column``."""
    left = keys[["player_id", date_column]].drop_duplicates().dropna()
    left = left.sort_values(date_column)
    right = (
        valuations[["player_id", "date", "market_value_in_eur"]]
        .dropna(subset=["date"])
        .sort_values("date")
    )
    merged = pd.merge_asof(
        left,
        right,
        left_on=date_column,
        right_on="date",
        by="player_id",
        direction="backward",
    )
    return merged.rename(columns={"market_value_in_eur": name, "date": f"{name}_date"})


def _team_games(games: pd.DataFrame) -> pd.DataFrame:
    home = games[["season", "competition_id", "home_club_id"]].rename(
        columns={"home_club_id": "club_id"}
    )
    away = games[["season", "competition_id", "away_club_id"]].rename(
        columns={"away_club_id": "club_id"}
    )
    both = pd.concat([home, away])
    return both.groupby(["season", "competition_id", "club_id"]).size().rename("team_games")


def _main_lineup_position(lineups: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    starts = lineups.loc[lineups["type"] == "starting_lineup", ["game_id", "player_id", "position"]]
    starts = starts.merge(games[["game_id", "season", "competition_id"]], on="game_id")
    counts = starts.groupby([*KEY, "position"]).size().rename("n").reset_index()
    counts = counts.sort_values([*KEY, "n", "position"], ascending=[True, True, True, False, True])
    main = counts.drop_duplicates(subset=KEY).rename(columns={"position": "main_lineup_position"})
    n_positions = counts.groupby(KEY).size().rename("n_lineup_positions")
    return main[[*KEY, "main_lineup_position"]].merge(n_positions.reset_index(), on=KEY)


def build_player_season(tables: Tables, stints: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build the player x season x competition table from normalized :class:`Tables`."""
    games = tables.games
    if stints is None:
        stints = build_stints(games, tables.appearances, tables.game_lineups, tables.game_events)

    game_info = games[["game_id", "season", "competition_id"]]
    st = stints.merge(game_info, on="game_id", how="inner")

    # Counting stats come from appearances (official), restricted to games with minutes.
    apps = tables.appearances.loc[tables.appearances["minutes_played"].fillna(0) > 0]
    apps = apps.drop(columns=["competition_id"], errors="ignore").merge(game_info, on="game_id")
    counting = apps.groupby(KEY)[["goals", "assists", "yellow_cards", "red_cards"]].sum()

    usage = st.groupby(KEY).agg(
        games=("game_id", "nunique"),
        starts=("started", "sum"),
        minutes=("minutes", "sum"),
        full_games=("minutes", lambda m: int((m >= MATCH_MINUTES).sum())),
        goals_for_on=("goals_for_on", "sum"),
        goals_against_on=("goals_against_on", "sum"),
        reconciled_minutes=(
            "minutes",
            lambda m: int(m[st.loc[m.index, "events_reconciled"]].sum()),
        ),
    )

    by_club = st.groupby([*KEY, "club_id"])["minutes"].sum().reset_index()
    by_club = by_club.sort_values(
        [*KEY, "minutes", "club_id"], ascending=[True] * 3 + [False, True]
    )
    main_club = by_club.drop_duplicates(subset=KEY)[[*KEY, "club_id"]]
    n_clubs = by_club.groupby(KEY).size().rename("n_clubs")

    df = usage.join(counting, how="left").join(n_clubs).reset_index().merge(main_club, on=KEY)
    df = df.merge(_team_games(games).reset_index(), on=["season", "competition_id", "club_id"])
    df["minutes_share"] = (df["minutes"] / (df["team_games"] * MATCH_MINUTES)).clip(upper=1.0)
    df["start_rate"] = df["starts"] / df["games"]

    for column in ("goals", "assists", "yellow_cards", "red_cards"):
        df[column] = df[column].fillna(0).astype("int64")
    df["goal_contributions"] = df["goals"] + df["assists"]
    df["plus_minus_on"] = df["goals_for_on"] - df["goals_against_on"]

    for source, target in PER90_SOURCES.items():
        on_pitch = source.endswith("_on")
        minutes = df["reconciled_minutes"] if on_pitch else df["minutes"]
        df[target] = _per90(df[source].astype("float64"), minutes)

    df = df.merge(_main_lineup_position(tables.game_lineups, games), on=KEY, how="left")
    df = _add_profile(df, tables)
    df = _add_market(df, tables)

    df["season_label"] = df["season"].map(season_label)
    df = df.merge(
        tables.clubs[["club_id", "name"]].rename(columns={"name": "club_name"}),
        on="club_id",
        how="left",
    )
    return df.sort_values([*KEY]).reset_index(drop=True)


def _add_profile(df: pd.DataFrame, tables: Tables) -> pd.DataFrame:
    players = tables.players[
        [
            "player_id",
            "name",
            "date_of_birth",
            "position",
            "sub_position",
            "foot",
            "height_in_cm",
            "country_of_citizenship",
            "contract_expiration_date",
            "current_club_id",
        ]
    ]
    df = df.merge(players, on="player_id", how="left")
    df["position_group"] = df["position"].map(POSITION_GROUPS)
    # Age at the season's reference date (1 January of the season's second year).
    reference = pd.to_datetime((df["season"] + 1).astype(str) + "-01-01").astype(DATE_DTYPE)
    df["age"] = ((reference - df["date_of_birth"]).dt.days / 365.25).round(1)
    return df


def _add_market(df: pd.DataFrame, tables: Tables) -> pd.DataFrame:
    """Market value at the start (1 July) and end (30 June) of each season."""
    keys = df[["player_id", "season"]].drop_duplicates().copy()
    keys["season_start"] = pd.to_datetime(keys["season"].astype(str) + "-07-01").astype(DATE_DTYPE)
    keys["season_end"] = pd.to_datetime((keys["season"] + 1).astype(str) + "-06-30").astype(
        DATE_DTYPE
    )
    start = _value_on_or_before(
        keys, tables.player_valuations, "season_start", "market_value_start"
    )
    end = _value_on_or_before(keys, tables.player_valuations, "season_end", "market_value_end")
    keys = keys.merge(start, on=["player_id", "season_start"], how="left")
    keys = keys.merge(end, on=["player_id", "season_end"], how="left")
    keys["market_value_change"] = keys["market_value_end"] - keys["market_value_start"]
    keys = keys.drop(columns=["season_start", "season_end"])
    df = df.merge(keys, on=["player_id", "season"], how="left")
    df["market_value_end"] = df["market_value_end"].astype("float64")
    df["log_market_value_end"] = np.log10(df["market_value_end"].where(df["market_value_end"] > 0))
    return df
