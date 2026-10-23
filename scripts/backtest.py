"""Backtest the value model on past seasons (docs/backtest.md).

Usage:
    python scripts/backtest.py                       # 2023/24 (1 and 2 years) and 2024/25 (1 year)
    python scripts/backtest.py --flag-ratio 0.7

Prints Markdown tables that reproduce every number in docs/backtest.md.
"""

from __future__ import annotations

import argparse

import pandas as pd

from scouting.app_data import build_app_data
from scouting.config import load_settings
from scouting.metrics.backtest import BacktestResult, run_backtest
from scouting.metrics.percentiles import percentile_ranks
from scouting.transform.tables import load_tables

RUNS = [(2023, 1), (2023, 2), (2024, 1)]


def _table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(map(str, df.columns)) + " |"
    rule = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def _summary_table(frame: pd.DataFrame, first: str) -> str:
    out = frame.reset_index().rename(columns={frame.index.name or "index": first})
    out["players"] = out["players"].astype(int)
    out["median_value_ratio"] = out["median_value_ratio"].map("{:.2f}x".format)
    out["median_value_change"] = out["median_value_change"].map("×{:.2f}".format)
    out["share_rose"] = out["share_rose"].map("{:.0%}".format)
    return _table(
        out.rename(
            columns={
                "players": "Players",
                "median_value_ratio": "Value vs expected (median)",
                "median_value_change": "Market value change (median)",
                "share_rose": "Value rose",
            }
        )
    )


def _report(r: BacktestResult) -> str:
    season = f"{r.base_season}/{(r.base_season + 1) % 100:02d}"
    lines = [
        f"## Base {season}, {r.horizon_years} year(s) later",
        "",
        f"Rated: {r.n_rated} · followed: {len(r.players)} "
        f"(flagged {r.followed_share_flagged:.0%}, others {r.followed_share_others:.0%})",
        "",
        _summary_table(r.quintiles, "Quintile (1 = cheapest for output)"),
        "",
        _summary_table(r.flagged_vs_others, f"Group (flag ≤ {r.flag_ratio:.2f}x)"),
        "",
        f"Like-for-like ({r.matched_n} flagged players matched): value change "
        f"×{r.matched_value_change:.2f} relative to others; share that rose "
        f"{r.matched_rose_diff:+.1f} points.",
        f"Regression: coefficient {r.regression_coef:.3f} (robust SE {r.regression_se:.3f}); "
        f"a player at half his expected value: ×{r.half_price_effect:.2f} relative.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--flag-ratio", type=float, default=0.5)
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    data = build_app_data(settings, today=pd.Timestamp.today().normalize())
    table = pd.read_parquet(settings.processed_dir / "player_season.parquet")
    ranked = percentile_ranks(table, min_minutes=settings.analysis.min_minutes)
    valuations = load_tables(settings.processed_dir / "transfermarkt").player_valuations

    for base, horizon in RUNS:
        result = run_backtest(
            ranked,
            data.league_strength,
            valuations,
            base_season=base,
            horizon_years=horizon,
            min_minutes=settings.analysis.min_minutes,
            flag_ratio=args.flag_ratio,
        )
        print(_report(result))
    print(
        f"Valuations to {pd.to_datetime(valuations['date']).max().date()} · transfermarkt-datasets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
