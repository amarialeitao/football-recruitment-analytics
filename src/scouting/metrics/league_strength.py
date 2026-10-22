"""League strength from two transparent signals, both taken from the same open source.

1. **Squad value:** the average total market value of a league's clubs at the end of the season
   (sum of the end-of-season market value of every player who played for the club).
   ``strength_index`` = that average relative to the focus league (focus league = 100).
2. **European results:** points per game and goal difference per game of the league's clubs
   against clubs from *other* leagues in UEFA club competitions in the same season (the source
   covers the Champions League and its qualifying rounds only). Shown next to
   the index as supporting evidence, with the number of games behind it.

Neither signal is hidden inside player metrics: pages show it next to percentiles.
"""

from __future__ import annotations

import pandas as pd


def squad_value_by_league(player_season: pd.DataFrame) -> pd.DataFrame:
    """Average club squad value per league and season (one row per competition and season)."""
    clubs = (
        player_season.groupby(["competition_id", "season", "club_id"])["market_value_end"]
        .sum(min_count=1)
        .rename("squad_value")
        .reset_index()
    )
    return (
        clubs.groupby(["competition_id", "season"])
        .agg(clubs=("club_id", "nunique"), avg_squad_value=("squad_value", "mean"))
        .reset_index()
    )


def _club_league_lookups(
    games: pd.DataFrame, clubs: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lookups from a club to its domestic league: per season, and current (fallback).

    Uses domestic games when available (correct for promoted and relegated clubs) and falls back
    to the club's current domestic league for clubs outside the project scope.
    """
    home = games[["home_club_id", "season", "competition_id"]].rename(
        columns={"home_club_id": "club_id"}
    )
    away = games[["away_club_id", "season", "competition_id"]].rename(
        columns={"away_club_id": "club_id"}
    )
    played = pd.concat([home, away]).drop_duplicates(subset=["club_id", "season"])
    fallback = clubs[["club_id", "domestic_competition_id"]].rename(
        columns={"domestic_competition_id": "fallback_competition_id"}
    )
    return played, fallback


def european_results(
    european_games: pd.DataFrame, games: pd.DataFrame, clubs: pd.DataFrame
) -> pd.DataFrame:
    """Points and goal difference per game of each league against other leagues in UEFA games."""
    played, fallback = _club_league_lookups(games, clubs)

    def side(prefix: str, other: str) -> pd.DataFrame:
        columns = ["game_id", "season", f"{prefix}_club_id", f"{prefix}_club_goals"]
        df = european_games[[*columns, f"{other}_club_goals"]].rename(
            columns={
                f"{prefix}_club_id": "club_id",
                f"{prefix}_club_goals": "goals_for",
                f"{other}_club_goals": "goals_against",
            }
        )
        return df

    # Note: the source only covers the Champions League (with qualifying) and the Super Cup, not
    # the Europa or Conference League, so game counts are small for some leagues.
    sides = pd.concat([side("home", "away"), side("away", "home")], ignore_index=True)
    sides = sides.merge(played, on=["club_id", "season"], how="left").merge(
        fallback, on="club_id", how="left"
    )
    sides["league"] = sides["competition_id"].fillna(sides["fallback_competition_id"])
    sides = sides.dropna(subset=["league", "goals_for", "goals_against"])

    # Keep only games between clubs of different leagues.
    leagues_per_game = sides.groupby("game_id")["league"].nunique()
    sides = sides[sides["game_id"].map(leagues_per_game) == 2]

    sides["points"] = (sides["goals_for"] > sides["goals_against"]) * 3 + (
        sides["goals_for"] == sides["goals_against"]
    ) * 1
    sides["goal_diff"] = sides["goals_for"] - sides["goals_against"]
    return (
        sides.groupby(["league", "season"])
        .agg(
            european_games=("game_id", "nunique"),
            european_ppg=("points", "mean"),
            european_goal_diff_pg=("goal_diff", "mean"),
        )
        .reset_index()
        .rename(columns={"league": "competition_id"})
    )


def league_strength(
    player_season: pd.DataFrame,
    european_games: pd.DataFrame,
    games: pd.DataFrame,
    clubs: pd.DataFrame,
    focus_competition: str,
) -> pd.DataFrame:
    """One row per competition and season with the squad-value index and European results."""
    value = squad_value_by_league(player_season)
    focus = value.loc[value["competition_id"] == focus_competition, ["season", "avg_squad_value"]]
    focus = focus.rename(columns={"avg_squad_value": "focus_avg_squad_value"})
    value = value.merge(focus, on="season", how="left")
    value["strength_index"] = 100 * value["avg_squad_value"] / value["focus_avg_squad_value"]
    value = value.drop(columns="focus_avg_squad_value")

    europe = european_results(european_games, games, clubs)
    out = value.merge(europe, on=["competition_id", "season"], how="left")
    out["european_games"] = out["european_games"].fillna(0).astype("int64")
    return out.sort_values(["season", "strength_index"], ascending=[True, False]).reset_index(
        drop=True
    )
