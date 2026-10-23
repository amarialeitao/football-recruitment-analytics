"""Reproduce the recruitment case study (docs/case-study.md) from the local data.

Usage:
    python scripts/case_study.py                     # default brief (right-back, €1.5m cap)
    python scripts/case_study.py --max-value 1000000 --max-age 26

Prints the reference profile, the shortlist and the three alternatives as Markdown tables.
"""

from __future__ import annotations

import argparse

import pandas as pd

from scouting.app_data import build_app_data
from scouting.case_study import Brief, pick_alternatives, shortlist
from scouting.config import load_settings
from scouting.insights import format_money

DEFAULTS = {
    "player": "Gaizka Larrazabal",
    "club": "Casa Pia AC",
    "season": 2025,
    "positions": ["Right-Back"],
    "max_value": 1_500_000,
    "max_age": 29,
    "min_minutes": 1800,
}

COLUMNS = {
    "name": "Player",
    "club_name": "Club",
    "competition_name": "League",
    "age": "Age",
    "minutes": "Min",
    "minutes_share": "Share of team min",
    "goal_contributions_p90": "G+A /90",
    "plus_minus_on_p90": "On-pitch +/- /90",
    "performance_score": "Perf. score",
    "market_value_end": "Value",
    "value_ratio": "Value vs expected",
    "contract_expiration_date": "Contract",
    "similarity": "Similarity",
}


def _table(df: pd.DataFrame) -> str:
    """Minimal Markdown table (no extra dependency)."""
    header = "| " + " | ".join(map(str, df.columns)) + " |"
    rule = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def _markdown(df: pd.DataFrame) -> str:
    out = df[[c for c in COLUMNS if c in df.columns]].rename(columns=COLUMNS).copy()
    formats = {
        "Age": "{:.1f}",
        "Share of team min": "{:.0%}",
        "G+A /90": "{:.2f}",
        "On-pitch +/- /90": "{:+.2f}",
        "Perf. score": "{:.0f}",
        "Value vs expected": "{:.2f}x",
        "Similarity": "{:.0f}",
    }
    for column, fmt in formats.items():
        if column in out:
            out[column] = out[column].map(lambda v, f=fmt: "—" if pd.isna(v) else f.format(v))
    if "Value" in out:
        out["Value"] = out["Value"].map(format_money)
    if "Contract" in out:
        out["Contract"] = out["Contract"].map(lambda d: "unknown" if pd.isna(d) else d.date())
    return _table(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--player", default=DEFAULTS["player"])
    parser.add_argument("--club", default=DEFAULTS["club"])
    parser.add_argument("--season", type=int, default=DEFAULTS["season"])
    parser.add_argument("--positions", nargs="+", default=DEFAULTS["positions"])
    parser.add_argument("--max-value", type=float, default=DEFAULTS["max_value"])
    parser.add_argument("--max-age", type=float, default=DEFAULTS["max_age"])
    parser.add_argument("--min-minutes", type=int, default=DEFAULTS["min_minutes"])
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    data = build_app_data(settings, today=pd.Timestamp.today().normalize())
    players = data.players
    match = players[
        (players["name"] == args.player)
        & (players["club_name"] == args.club)
        & (players["season"] == args.season)
    ]
    if match.empty:
        raise SystemExit(f"No row for {args.player} ({args.club}, season {args.season}).")
    ref = match.iloc[0]

    brief = Brief(
        reference={k: ref[k] for k in ("player_id", "season", "competition_id")},
        positions=args.positions,
        max_market_value=args.max_value,
        max_age=args.max_age,
        min_minutes=args.min_minutes,
        exclude_club_ids=[int(ref["club_id"])],
    )
    candidates = shortlist(players, brief, comparison_min_minutes=settings.analysis.min_minutes)
    picks = pick_alternatives(candidates, brief)

    print(f"## Reference: {ref['name']} ({ref['club_name']}, {ref['season_label']})\n")
    print(_markdown(match.head(1)), "\n")
    print(f"## Shortlist: {len(candidates)} candidates (top 10 by similarity)\n")
    print(_markdown(candidates.head(10)), "\n")
    print("## Alternatives\n")
    print(_markdown(picks.assign(name=picks["pick"] + ": " + picks["name"])))
    print(f"\nData to {data.data_cutoff.date()} · source: transfermarkt-datasets (CC0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
