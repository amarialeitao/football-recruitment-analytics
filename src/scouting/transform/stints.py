"""On-pitch intervals per player and game, and the goals scored while each player was on.

A *stint* is the interval ``(start, end]`` in match minutes during which a player was on the
pitch. ``start`` is 0 for starters and the substitution minute for players who came on (falling
back to ``90 - minutes_played`` when no substitution event exists). ``end`` is
``start + minutes_played`` capped at 90, so official minutes are always respected.

Goal events carry the club that benefited from the goal (own goals included), which matches the
final score in practically every game. Games where event goals do not add up to the final score
are kept but marked ``events_reconciled = False``, and their on-pitch goals are left empty.
"""

from __future__ import annotations

import pandas as pd

MATCH_MINUTES = 90


def reconcile_goal_events(games: pd.DataFrame, events: pd.DataFrame) -> pd.Series:
    """Return a boolean Series indexed by ``game_id``: do goal events match the final score?"""
    goals = events[events["type"] == "Goals"]
    per_club = goals.groupby(["game_id", "club_id"]).size().rename("n").reset_index()

    g = games[["game_id", "home_club_id", "away_club_id", "home_club_goals", "away_club_goals"]]
    home = g.merge(
        per_club, left_on=["game_id", "home_club_id"], right_on=["game_id", "club_id"], how="left"
    )["n"].fillna(0)
    away = g.merge(
        per_club, left_on=["game_id", "away_club_id"], right_on=["game_id", "club_id"], how="left"
    )["n"].fillna(0)
    ok = (home.to_numpy() == g["home_club_goals"].to_numpy()) & (
        away.to_numpy() == g["away_club_goals"].to_numpy()
    )
    return pd.Series(ok, index=g["game_id"].to_numpy(), name="events_reconciled")


def build_stints(
    games: pd.DataFrame,
    appearances: pd.DataFrame,
    lineups: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """One row per player and game with minutes, stint bounds and on-pitch goals.

    Columns: ``game_id, player_id, club_id, started, start, end, minutes,
    events_reconciled, goals_for_on, goals_against_on``.
    """
    apps = appearances.loc[
        appearances["minutes_played"].fillna(0) > 0,
        ["game_id", "player_id", "player_club_id", "minutes_played"],
    ].rename(columns={"player_club_id": "club_id", "minutes_played": "minutes"})
    apps["minutes"] = apps["minutes"].clip(upper=MATCH_MINUTES)

    starters = lineups.loc[lineups["type"] == "starting_lineup", ["game_id", "player_id"]]
    starters = starters.drop_duplicates().assign(started=True)

    subs_in = (
        events.loc[events["type"] == "Substitutions", ["game_id", "player_in_id", "minute"]]
        .dropna(subset=["player_in_id"])
        .rename(columns={"player_in_id": "player_id", "minute": "sub_in_minute"})
        .drop_duplicates(subset=["game_id", "player_id"])
    )

    stints = apps.merge(starters, on=["game_id", "player_id"], how="left")
    stints["started"] = stints["started"].fillna(False).astype(bool)
    stints = stints.merge(subs_in, on=["game_id", "player_id"], how="left")

    sub_minute = stints["sub_in_minute"].where(stints["sub_in_minute"].between(0, MATCH_MINUTES))
    fallback = MATCH_MINUTES - stints["minutes"]
    start = sub_minute.fillna(fallback).where(~stints["started"], 0)
    stints["start"] = start.astype("int64")
    stints["end"] = (stints["start"] + stints["minutes"]).clip(upper=MATCH_MINUTES).astype("int64")
    stints = stints.drop(columns="sub_in_minute")

    reconciled = reconcile_goal_events(games, events)
    stints["events_reconciled"] = (
        stints["game_id"].map(reconciled).fillna(False).astype(bool).to_numpy()
    )

    goals = events.loc[events["type"] == "Goals", ["game_id", "club_id", "minute"]].rename(
        columns={"club_id": "scoring_club_id"}
    )
    on = stints[["game_id", "player_id", "club_id", "start", "end"]].merge(goals, on="game_id")
    on = on[(on["minute"] > on["start"]) & (on["minute"] <= on["end"])]
    on["for"] = (on["scoring_club_id"] == on["club_id"]).astype(int)
    on["against"] = 1 - on["for"]
    counts = on.groupby(["game_id", "player_id"])[["for", "against"]].sum()

    stints = stints.merge(counts, on=["game_id", "player_id"], how="left")
    for column, name in (("for", "goals_for_on"), ("against", "goals_against_on")):
        values = stints[column].fillna(0)
        stints[name] = values.where(stints["events_reconciled"]).astype("Float64")
    stints = stints.drop(columns=["for", "against"])
    stints["minutes"] = stints["minutes"].astype("int64")
    return stints[
        [
            "game_id",
            "player_id",
            "club_id",
            "started",
            "start",
            "end",
            "minutes",
            "events_reconciled",
            "goals_for_on",
            "goals_against_on",
        ]
    ]
