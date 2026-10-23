"""Insight engine: short automatic texts, each with the evidence and a confidence badge.

Rules (same philosophy for every insight):

* **Confidence comes from the sample.** For a player, the sample is minutes played; for a group,
  the number of players. When several samples are involved, the weakest one decides.
* **Observation vs interpretation.** Observations state a fact and are always shown.
  Interpretations read the facts; their wording softens when confidence is low.
* **Evidence travels with the text.** Every insight carries the numbers behind it, so the UI
  can show "observed data" separately from the reading.
* **Two languages.** Texts exist in English and Portuguese; the UI picks one.

Insights never invent numbers: if an input is missing, the generator returns nothing.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.metrics.percentiles import PCT_SUFFIX

Confidence = Literal["low", "medium", "high"]
Kind = Literal["observation", "interpretation"]
Lang = Literal["en", "pt"]

LOW: Confidence = "low"
MEDIUM: Confidence = "medium"
HIGH: Confidence = "high"
_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}

CONFIDENCE_LABEL = {
    "en": {LOW: "low confidence", MEDIUM: "medium confidence", HIGH: "high confidence"},
    "pt": {LOW: "confiança baixa", MEDIUM: "confiança média", HIGH: "confiança alta"},
}

POSITION_LABEL = {
    "en": {
        "Forward": "forwards",
        "Midfielder": "midfielders",
        "Defender": "defenders",
        "Goalkeeper": "goalkeepers",
    },
    "pt": {
        "Forward": "avançados",
        "Midfielder": "médios",
        "Defender": "defesas",
        "Goalkeeper": "guarda-redes",
    },
}

STRENGTH_PCT = 75.0
WEAKNESS_PCT = 25.0
UNDERVALUED_RATIO = 0.7
OVERVALUED_RATIO = 1.5


@dataclass(frozen=True)
class Insight:
    """One automatic finding. ``text`` and ``title`` hold one string per language."""

    key: str
    text: dict[str, str]
    confidence: Confidence
    kind: Kind = "interpretation"
    sample: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def reliable(self) -> bool:
        """Enough evidence to be read as a firm conclusion."""
        return self.confidence != LOW

    def render(self, lang: Lang = "en") -> str:
        return self.text[lang]

    def title(self, lang: Lang = "en", max_chars: int = 110) -> str:
        """Action title: the first sentence of the text, without the final period."""
        first = self.text[lang].split(". ")[0].rstrip(". ")
        return first if len(first) <= max_chars else first[: max_chars - 1].rstrip() + "…"


# --- confidence --------------------------------------------------------------------------------


def confidence_from_sample(*samples: float | int | None, medium: int, high: int) -> Confidence:
    """Most conservative level among the samples. No usable sample -> low."""
    usable = [s for s in samples if s is not None and not pd.isna(s)]
    if not usable:
        return LOW
    smallest = min(usable)
    if smallest >= high:
        return HIGH
    if smallest >= medium:
        return MEDIUM
    return LOW


def weakest(*levels: Confidence) -> Confidence:
    """The lowest of several confidence levels."""
    return min(levels, key=_ORDER.__getitem__)


def pick_variant(options: Sequence[str], key: str) -> str:
    """Choose a template deterministically from ``key`` (stable across runs, unlike ``hash``)."""
    return options[zlib.crc32(key.encode("utf-8")) % len(options)]


# --- formatting --------------------------------------------------------------------------------


def format_money(value: float | None, lang: Lang = "en") -> str:
    """EUR amounts as '€1.2m' / '€850k' (Portuguese uses a decimal comma)."""
    if value is None or pd.isna(value):
        return "—"
    if value >= 1e6:
        text = f"€{value / 1e6:.1f}m"
    elif value >= 1e3:
        text = f"€{value / 1e3:.0f}k"
    else:
        text = f"€{value:.0f}"
    return text.replace(".", ",") if lang == "pt" else text


def format_int(value: int, lang: Lang = "en") -> str:
    """Thousands separator: '1,234' in English, '1.234' in Portuguese."""
    text = f"{int(value):,}"
    return text.replace(",", ".") if lang == "pt" else text


def format_decimal(value: float, lang: Lang = "en", digits: int = 1) -> str:
    """'26.4' in English, '26,4' in Portuguese."""
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if lang == "pt" else text


def _top_share(pct: float) -> int:
    """Percentile 92 -> 'top 8%' (never 'top 0%')."""
    return max(1, round(100 - pct))


# --- player insights ---------------------------------------------------------------------------


def player_insights(
    row: pd.Series,
    *,
    confidence_minutes: tuple[int, int],
    min_minutes: int,
    sample_thresholds: tuple[int, int] = (30, 100),
) -> list[Insight]:
    """Strengths, weaknesses and the value reading for one player-season row.

    ``row`` must come from a table with percentiles (and optionally value columns).
    ``confidence_minutes`` is ``(medium, high)`` for the player's minutes and
    ``sample_thresholds`` is ``(medium, high)`` for the size of the comparison group.
    """
    insights: list[Insight] = []
    minutes = int(row["minutes"])
    group = row.get("position_group")
    medium, high = confidence_minutes

    if minutes < min_minutes or group not in PROFILE_METRICS:
        insights.append(_small_sample(row, min_minutes))
        return insights

    player_conf = confidence_from_sample(minutes, medium=medium, high=high)
    comparison_n = row.get("comparison_n")
    group_conf = confidence_from_sample(
        comparison_n, medium=sample_thresholds[0], high=sample_thresholds[1]
    )
    conf = weakest(player_conf, group_conf)

    pcts = {
        key: float(row[key + PCT_SUFFIX])
        for key in PROFILE_METRICS[group]
        if key + PCT_SUFFIX in row and not pd.isna(row[key + PCT_SUFFIX])
    }
    strengths = sorted(((p, k) for k, p in pcts.items() if p >= STRENGTH_PCT), reverse=True)[:2]
    weaknesses = sorted((p, k) for k, p in pcts.items() if p <= WEAKNESS_PCT)[:2]

    for pct, key in strengths:
        insights.append(_strength(row, key, pct, conf, minutes, comparison_n))
    for pct, key in weaknesses:
        insights.append(_weakness(row, key, pct, conf, minutes, comparison_n))

    value = _value(row, conf, minutes)
    if value is not None:
        insights.append(value)
    return insights


def _strength(row, key, pct, conf, minutes, n) -> Insight:
    m = metric(key)
    share = _top_share(pct)
    group = row["position_group"]
    en_pos, pt_pos = POSITION_LABEL["en"][group], POSITION_LABEL["pt"][group]
    if conf == LOW:
        en = f"Early signal: {m.label.lower()} is in the top {share}% of {en_pos} in the sample"
        pt = f"Sinal inicial: {m.label_pt.lower()} entre os {share}% melhores {pt_pos} da amostra"
    else:
        en = pick_variant(
            [
                f"Top {share}% of {en_pos} for {m.label.lower()}",
                f"{m.label} is among the best {share}% of {en_pos}",
            ],
            f"{key}-{row['player_id']}",
        )
        pt = f"{m.label_pt} entre os {share}% melhores {pt_pos}"
    return Insight(
        key=f"strength:{key}",
        text={"en": en + ".", "pt": pt + "."},
        confidence=conf,
        sample=minutes,
        evidence={"metric": key, "value": row[key], "percentile": pct, "comparison_n": n},
    )


def _weakness(row, key, pct, conf, minutes, n) -> Insight:
    m = metric(key)
    # Share of peers with a better value; capped at 99 so the worst player never reads as
    # "worse than 100%" (he cannot be worse than himself), mirroring "never top 0%".
    better_than = min(99, round(100 - pct))
    group = row["position_group"]
    en_pos, pt_pos = POSITION_LABEL["en"][group], POSITION_LABEL["pt"][group]
    en = f"{m.label}: worse than {better_than}% of {en_pos}"
    pt = f"{m.label_pt}: pior que {better_than}% dos {pt_pos}"
    return Insight(
        key=f"weakness:{key}",
        text={"en": en + ".", "pt": pt + "."},
        confidence=conf,
        sample=minutes,
        evidence={"metric": key, "value": row[key], "percentile": pct, "comparison_n": n},
    )


def _value(row: pd.Series, conf: Confidence, minutes: int) -> Insight | None:
    ratio = row.get("value_ratio")
    if ratio is None or pd.isna(ratio) or bool(row.get("market_value_stale", False)):
        return None
    actual, expected = row["market_value_end"], row["expected_market_value"]
    evidence = {"market_value": actual, "expected_market_value": expected, "value_ratio": ratio}
    if ratio <= UNDERVALUED_RATIO:
        en = (
            f"Valued at {format_money(actual)}, below the {format_money(expected)} that players "
            "with similar output, age and league are usually valued at"
        )
        pt = (
            f"Avaliado em {format_money(actual, 'pt')}, abaixo dos {format_money(expected, 'pt')} "
            "de jogadores com produção, idade e liga parecidas"
        )
    elif ratio >= OVERVALUED_RATIO:
        en = (
            f"Valued at {format_money(actual)}, above the {format_money(expected)} expected for "
            "this output, age and league"
        )
        pt = (
            f"Avaliado em {format_money(actual, 'pt')}, acima dos {format_money(expected, 'pt')} "
            "esperados para esta produção, idade e liga"
        )
    else:
        return None
    suffix_en = ". Market value is an estimate, not a transfer fee."
    suffix_pt = ". Valor de mercado é uma estimativa, não um preço de transferência."
    return Insight(
        key="value",
        text={"en": en + suffix_en, "pt": pt + suffix_pt},
        confidence=conf,
        sample=minutes,
        evidence=evidence,
    )


def _small_sample(row: pd.Series, min_minutes: int) -> Insight:
    minutes = int(row["minutes"])
    return Insight(
        key="small_sample",
        text={
            "en": f"Only {format_int(minutes)} minutes played (minimum for comparisons: "
            f"{format_int(min_minutes)}). Percentiles are not shown; treat any number as a first "
            "impression.",
            "pt": f"Apenas {format_int(minutes, 'pt')} minutos jogados (mínimo para comparações: "
            f"{format_int(min_minutes, 'pt')}). Percentis não são mostrados; trate qualquer "
            "número como primeira impressão.",
        },
        confidence=LOW,
        kind="observation",
        sample=minutes,
        evidence={"minutes": minutes, "min_minutes": min_minutes},
    )


# --- market overview insights ------------------------------------------------------------------


def market_insights(
    player_season: pd.DataFrame,
    strength: pd.DataFrame,
    *,
    competition_id: str,
    competition_name: str,
    season: int,
    min_minutes: int,
    sample_thresholds: tuple[int, int] = (30, 100),
) -> list[Insight]:
    """Headline facts about one league and season for the Market Overview page."""
    league = player_season[
        (player_season["competition_id"] == competition_id) & (player_season["season"] == season)
    ]
    regulars = league[league["minutes"] >= min_minutes]
    if regulars.empty:
        return []
    medium, high = sample_thresholds
    n = len(regulars)
    conf = confidence_from_sample(n, medium=medium, high=high)
    out: list[Insight] = []

    median_age = float(regulars["age"].median())
    median_value = float(regulars["market_value_end"].median())
    out.append(
        Insight(
            key="league_size",
            text={
                "en": f"{n} players reached {format_int(min_minutes)} minutes in "
                f"{competition_name}; "
                f"their median age is {median_age:.1f} and median value "
                f"{format_money(median_value)}.",
                "pt": f"{n} jogadores chegaram a {format_int(min_minutes, 'pt')} minutos na "
                f"{competition_name}; idade mediana {format_decimal(median_age, 'pt')} e valor "
                f"mediano {format_money(median_value, 'pt')}.",
            },
            confidence=conf,
            kind="observation",
            sample=n,
            evidence={"players": n, "median_age": median_age, "median_value": median_value},
        )
    )

    u23 = regulars[regulars["age"] < 23]
    share_minutes = float(u23["minutes"].sum() / regulars["minutes"].sum())
    out.append(
        Insight(
            key="young_minutes",
            text={
                "en": f"Under-23 players took {share_minutes:.0%} of the minutes played by "
                f"regulars ({len(u23)} players).",
                "pt": f"Jogadores sub-23 somaram {share_minutes:.0%} dos minutos dos titulares "
                f"habituais ({len(u23)} jogadores).",
            },
            confidence=confidence_from_sample(len(u23), medium=medium, high=high),
            kind="observation",
            sample=len(u23),
            evidence={"u23_players": len(u23), "u23_minutes_share": share_minutes},
        )
    )

    season_strength = strength[strength["season"] == season].sort_values(
        "strength_index", ascending=False
    )
    if competition_id in set(season_strength["competition_id"]):
        rank = int(season_strength["competition_id"].tolist().index(competition_id) + 1)
        total = len(season_strength)
        row = season_strength[season_strength["competition_id"] == competition_id].iloc[0]
        out.append(
            Insight(
                key="league_rank",
                text={
                    "en": f"{competition_name} ranks {rank} of {total} leagues in scope by "
                    f"average squad value ({format_money(row['avg_squad_value'])} per club).",
                    "pt": f"A {competition_name} é a {rank}ª de {total} ligas pelo valor médio "
                    f"dos plantéis ({format_money(row['avg_squad_value'], 'pt')} por clube).",
                },
                confidence=HIGH,
                kind="observation",
                sample=int(row["clubs"]),
                evidence={"rank": rank, "of": total, "strength_index": row["strength_index"]},
            )
        )
    return out


def sort_insights(insights: Iterable[Insight]) -> list[Insight]:
    """Observations first, then interpretations by confidence (high first)."""
    return sorted(insights, key=lambda i: (i.kind != "observation", -_ORDER[i.confidence], i.key))
