"""Data checks on the analysis table: explicit rules that stop the build when broken.

Two kinds of rule:

* **error**: something the analysis relies on is wrong (duplicate rows, impossible minutes,
  shares above 100%...). ``scripts/build_dataset.py`` refuses to write the table, so a broken
  table never reaches the app.
* **warning**: a likely mistake in the source data in a field the analysis does not depend on
  (a height of 19 cm, a contract that ended before the season). Reported, never blocking.

Plausibility bounds come from ``checks`` in ``config/settings.yaml``. Each result keeps a few
example rows so a failure can be looked up quickly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

from scouting.config import Settings

KEY = ["player_id", "season", "competition_id"]
EXAMPLE_COLUMNS = ["name", "season", "competition_id"]
MAX_EXAMPLES = 3


@dataclass(frozen=True)
class CheckResult:
    name: str
    rule: dict[str, str]  # plain-language rule, per language
    severity: str  # "error" or "warning"
    failing: int
    examples: list[dict[str, object]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failing == 0


class DataCheckError(ValueError):
    """At least one error-level check failed; the message lists them."""


@dataclass(frozen=True)
class _Rule:
    name: str
    en: str
    pt: str
    severity: str
    bad: Callable[[pd.DataFrame], pd.Series]  # True for rows that break the rule


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce").astype("float64")


def _rules(settings: Settings) -> list[_Rule]:
    c = settings.checks
    seasons = set(settings.scope.seasons)
    competitions = set(settings.scope.competition_ids)
    age_lo, age_hi = c.age_range
    h_lo, h_hi = c.height_cm_range
    return [
        _Rule(
            "unique_rows",
            "One row per player, season and league",
            "Uma linha por jogador, época e liga",
            "error",
            lambda df: df.duplicated(KEY, keep=False),
        ),
        _Rule(
            "ids_present",
            "Player, season, league and club are always filled",
            "Jogador, época, liga e clube estão sempre preenchidos",
            "error",
            lambda df: df[[*KEY, "club_id"]].isna().any(axis=1),
        ),
        _Rule(
            "in_scope",
            "Only the leagues and seasons in the configuration",
            "Só as ligas e épocas da configuração",
            "error",
            lambda df: ~df["season"].isin(seasons) | ~df["competition_id"].isin(competitions),
        ),
        _Rule(
            "minutes_range",
            "Minutes are positive and at most 90 per game played",
            "Os minutos são positivos e no máximo 90 por jogo",
            "error",
            lambda df: (_num(df, "minutes") <= 0) | (_num(df, "minutes") > _num(df, "games") * 90),
        ),
        _Rule(
            "starts_le_games",
            "Starts never exceed games played",
            "As titularidades nunca excedem os jogos",
            "error",
            lambda df: _num(df, "starts") > _num(df, "games"),
        ),
        _Rule(
            "games_le_team_games",
            "A player who stayed at one club plays at most his team's games",
            "Um jogador que ficou num só clube joga no máximo os jogos da equipa",
            "error",
            lambda df: (df["n_clubs"] == 1) & (_num(df, "games") > _num(df, "team_games")),
        ),
        _Rule(
            "shares_0_1",
            "Share of team minutes and start rate are between 0% and 100%",
            "A % dos minutos da equipa e a % de titularidades estão entre 0% e 100%",
            "error",
            lambda df: (
                ~_num(df, "minutes_share").between(0, 1) | ~_num(df, "start_rate").between(0, 1)
            ),
        ),
        _Rule(
            "counts_non_negative",
            "Goals, assists and cards are never negative",
            "Golos, assistências e cartões nunca são negativos",
            "error",
            lambda df: (df[["goals", "assists", "yellow_cards", "red_cards"]] < 0).any(axis=1),
        ),
        _Rule(
            "on_pitch_goals",
            "On-pitch goal difference equals goals scored minus conceded",
            "O saldo em campo é igual a golos marcados menos sofridos",
            "error",
            lambda df: (
                (
                    _num(df, "plus_minus_on")
                    - (_num(df, "goals_for_on") - _num(df, "goals_against_on"))
                ).abs()
                > 1e-9
            ),
        ),
        _Rule(
            "age_plausible",
            f"Age is between {age_lo:g} and {age_hi:g} when known",
            f"A idade está entre {age_lo:g} e {age_hi:g} quando conhecida",
            "error",
            lambda df: _num(df, "age").notna() & ~_num(df, "age").between(age_lo, age_hi),
        ),
        _Rule(
            "market_value_plausible",
            f"Market values are above €0 and at most €{c.market_value_max / 1e6:,.0f}m",
            f"Os valores de mercado são acima de €0 e no máximo €{c.market_value_max / 1e6:,.0f}m",
            "error",
            lambda df: pd.concat(
                [
                    _num(df, col).notna()
                    & ((_num(df, col) <= 0) | (_num(df, col) > c.market_value_max))
                    for col in ("market_value_start", "market_value_end")
                ],
                axis=1,
            ).any(axis=1),
        ),
        _Rule(
            "height_plausible",
            f"Height is between {h_lo:g} and {h_hi:g} cm when known (not used in the analysis)",
            f"A altura está entre {h_lo:g} e {h_hi:g} cm quando conhecida (não é usada na análise)",
            "warning",
            lambda df: (
                _num(df, "height_in_cm").notna() & ~_num(df, "height_in_cm").between(h_lo, h_hi)
            ),
        ),
        _Rule(
            "contract_not_expired",
            "The contract had not already ended before the season started",
            "O contrato não tinha terminado antes do início da época",
            "warning",
            lambda df: (
                df["contract_expiration_date"].notna()
                & (
                    df["contract_expiration_date"]
                    < pd.to_datetime(df["season"].astype("string") + "-07-01")
                )
            ),
        ),
        _Rule(
            "position_known",
            "Position is known (players without one are left out of comparisons)",
            "A posição é conhecida (jogadores sem posição ficam fora das comparações)",
            "warning",
            lambda df: df["position_group"].isna(),
        ),
    ]


def run_checks(df: pd.DataFrame, settings: Settings) -> list[CheckResult]:
    """Run every rule on the player-season table (built, before percentiles)."""
    results = []
    for rule in _rules(settings):
        bad = rule.bad(df).fillna(False).astype(bool)
        examples = (
            df.loc[bad, [c for c in EXAMPLE_COLUMNS if c in df.columns]]
            .head(MAX_EXAMPLES)
            .astype("object")
            .to_dict("records")
        )
        results.append(
            CheckResult(
                name=rule.name,
                rule={"en": rule.en, "pt": rule.pt},
                severity=rule.severity,
                failing=int(bad.sum()),
                examples=examples,
            )
        )
    return results


def errors(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if r.severity == "error" and not r.passed]


def warnings(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if r.severity == "warning" and not r.passed]


def report(results: list[CheckResult]) -> str:
    """Plain-text summary for the command line."""
    lines = []
    for r in results:
        status = "ok" if r.passed else r.severity.upper()
        rows = "1 row" if r.failing == 1 else f"{r.failing} rows"
        detail = "" if r.passed else f" ({rows}, e.g. {r.examples})"
        lines.append(f"  [{status:>7}] {r.rule['en']}{detail}")
    return "\n".join(lines)


def assert_valid(results: list[CheckResult]) -> None:
    """Raise :class:`DataCheckError` if any error-level check failed."""
    failed = errors(results)
    if failed:
        names = ", ".join(f"{r.name} ({r.failing} rows)" for r in failed)
        raise DataCheckError(f"Data checks failed: {names}\n{report(results)}")
