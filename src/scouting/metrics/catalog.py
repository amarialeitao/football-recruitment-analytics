"""Catalog of player metrics: label, unit, direction and the default profile per position group.

Every page and metric function reads metric definitions from here, so a label or a direction
("lower is better") is defined once.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    label_pt: str
    higher_is_better: bool = True
    fmt: str = "{:.2f}"
    description: str = ""


METRICS: dict[str, Metric] = {
    m.key: m
    for m in (
        Metric("minutes", "Minutes", "Minutos", fmt="{:,.0f}"),
        Metric(
            "minutes_share",
            "Share of team minutes",
            "% dos minutos da equipa",
            fmt="{:.0%}",
            description="Minutes played / (team league games x 90).",
        ),
        Metric("start_rate", "Start rate", "% de titularidades", fmt="{:.0%}"),
        Metric("goals_p90", "Goals per 90", "Golos por 90"),
        Metric("assists_p90", "Assists per 90", "Assistências por 90"),
        Metric("goal_contributions_p90", "Goals + assists per 90", "Golos + assistências por 90"),
        Metric(
            "goals_for_on_p90",
            "Team goals scored per 90 (on pitch)",
            "Golos da equipa por 90 (em campo)",
            description="Goals scored by the player's team while he was on the pitch.",
        ),
        Metric(
            "goals_against_on_p90",
            "Team goals conceded per 90 (on pitch)",
            "Golos sofridos por 90 (em campo)",
            higher_is_better=False,
            description="Goals conceded by the player's team while he was on the pitch.",
        ),
        Metric(
            "plus_minus_on_p90",
            "On-pitch goal difference per 90",
            "Saldo de golos por 90 (em campo)",
            description="Team goals scored minus conceded while on the pitch. Reflects the team as "
            "much as the player.",
        ),
        Metric(
            "yellow_cards_p90", "Yellow cards per 90", "Amarelos por 90", higher_is_better=False
        ),
    )
}

PROFILE_METRICS: dict[str, tuple[str, ...]] = {
    "Forward": (
        "goals_p90",
        "assists_p90",
        "goal_contributions_p90",
        "goals_for_on_p90",
        "plus_minus_on_p90",
        "minutes_share",
        "start_rate",
    ),
    "Midfielder": (
        "goal_contributions_p90",
        "assists_p90",
        "goals_for_on_p90",
        "goals_against_on_p90",
        "plus_minus_on_p90",
        "minutes_share",
        "yellow_cards_p90",
    ),
    "Defender": (
        "goals_against_on_p90",
        "plus_minus_on_p90",
        "goal_contributions_p90",
        "minutes_share",
        "start_rate",
        "yellow_cards_p90",
    ),
    "Goalkeeper": (
        "goals_against_on_p90",
        "plus_minus_on_p90",
        "minutes_share",
        "start_rate",
    ),
}

# Metrics the public data cannot provide; pages show them as "not available" instead of hiding
# the gap.
UNAVAILABLE_METRICS: tuple[dict[str, str], ...] = (
    {
        "en": "Expected goals (xG) and expected assists (xA)",
        "pt": "Golos esperados (xG) e assistências esperadas (xA)",
    },
    {"en": "Shots and shot quality", "pt": "Remates e qualidade dos remates"},
    {
        "en": "Passes, progressive passes and carries",
        "pt": "Passes, passes progressivos e conduções",
    },
    {
        "en": "Defensive actions (tackles, interceptions, pressures)",
        "pt": "Ações defensivas (desarmes, interceções, pressões)",
    },
    {"en": "Aerial and ground duels", "pt": "Duelos aéreos e no chão"},
)


def metric(key: str) -> Metric:
    """Return the :class:`Metric` for ``key`` (raises ``KeyError`` with the known keys)."""
    try:
        return METRICS[key]
    except KeyError:
        raise KeyError(f"Unknown metric '{key}'. Known: {sorted(METRICS)}") from None
