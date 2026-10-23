"""Insight engine tests. All data is invented."""

from __future__ import annotations

import pandas as pd
import pytest

from scouting import insights as ins
from scouting.metrics.percentiles import PCT_SUFFIX, percentile_ranks

CONF_MIN = (900, 1800)


# --- confidence and formatting -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("samples", "expected"),
    [
        ((2000,), "high"),
        ((1000,), "medium"),
        ((500,), "low"),
        ((2000, 500), "low"),  # the weakest sample decides
        ((None,), "low"),
        ((), "low"),
    ],
)
def test_confidence_from_sample(samples, expected) -> None:
    assert ins.confidence_from_sample(*samples, medium=900, high=1800) == expected


def test_weakest() -> None:
    assert ins.weakest("high", "medium") == "medium"
    assert ins.weakest("high", "low", "medium") == "low"


def test_pick_variant_is_deterministic() -> None:
    options = ["a", "b", "c"]
    assert ins.pick_variant(options, "same-key") == ins.pick_variant(options, "same-key")


@pytest.mark.parametrize(
    ("value", "lang", "expected"),
    [
        (1_250_000, "en", "€1.2m"),
        (1_250_000, "pt", "€1,2m"),
        (850_000, "en", "€850k"),
        (None, "en", "—"),
    ],
)
def test_format_money(value, lang, expected) -> None:
    assert ins.format_money(value, lang) == expected


def test_format_numbers_by_language() -> None:
    assert ins.format_int(12345, "en") == "12,345"
    assert ins.format_int(12345, "pt") == "12.345"
    assert ins.format_decimal(26.44, "pt") == "26,4"


def test_title_is_first_sentence_without_period() -> None:
    insight = ins.Insight("k", {"en": "First claim. Second.", "pt": "Primeira. Segunda."}, "high")
    assert insight.title("en") == "First claim"
    long = ins.Insight("k", {"en": "x" * 200, "pt": "y"}, "high")
    assert len(long.title("en", max_chars=50)) == 50


# --- player insights ---------------------------------------------------------------------------


@pytest.fixture
def ranked(ps: pd.DataFrame) -> pd.DataFrame:
    return percentile_ranks(ps, min_minutes=900)


def _best_forward(ranked: pd.DataFrame) -> pd.Series:
    fwd = ranked[(ranked["position_group"] == "Forward") & (ranked["minutes"] >= 1800)]
    return fwd.loc[fwd["goals_p90"].idxmax()]


def test_player_strengths_name_metric_and_carry_evidence(ranked: pd.DataFrame) -> None:
    row = _best_forward(ranked)
    out = ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
    strengths = [i for i in out if i.key.startswith("strength:")]
    assert 1 <= len(strengths) <= 2
    first = strengths[0]
    # High on minutes, but only ~30 synthetic forwards are compared: the group sample decides.
    assert first.confidence == "medium"
    assert first.evidence["percentile"] >= ins.STRENGTH_PCT
    assert first.evidence["comparison_n"] == row["comparison_n"]
    assert "forwards" in first.render("en")
    assert "avançados" in first.render("pt")


def test_weakness_wording_is_unambiguous(ranked: pd.DataFrame) -> None:
    fwd = ranked[(ranked["position_group"] == "Forward") & (ranked["minutes"] >= 900)]
    row = fwd.loc[fwd["goals_p90"].idxmin()]
    weak = [
        i
        for i in ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
        if i.key.startswith("weakness:")
    ]
    assert weak
    assert "worse than" in weak[0].render("en")
    assert "pior que" in weak[0].render("pt")


def test_low_minutes_soften_wording(ranked: pd.DataFrame) -> None:
    row = _best_forward(ranked).copy()
    row["minutes"] = 1000  # medium
    medium = ins.player_insights(row, confidence_minutes=(900, 1800), min_minutes=900)
    assert all(i.confidence == "medium" for i in medium)
    low = ins.player_insights(row, confidence_minutes=(1500, 3000), min_minutes=900)
    texts = [i.render("en") for i in low if i.key.startswith("strength:")]
    assert texts and all(t.startswith("Early signal") for t in texts)


def test_small_comparison_group_lowers_confidence(ranked: pd.DataFrame) -> None:
    row = _best_forward(ranked).copy()
    row["comparison_n"] = 12
    out = ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
    assert all(i.confidence == "low" for i in out)


def test_below_minimum_returns_only_small_sample_note(ranked: pd.DataFrame) -> None:
    row = ranked[ranked["minutes"] < 900].iloc[0]
    out = ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
    assert [i.key for i in out] == ["small_sample"]
    assert out[0].kind == "observation" and out[0].confidence == "low"


def test_value_insight_only_for_clear_gaps(ranked: pd.DataFrame) -> None:
    row = _best_forward(ranked).copy()
    row["market_value_stale"] = False
    row["market_value_end"], row["expected_market_value"] = 1e6, 4e6
    row["value_ratio"] = 0.25
    value = [
        i
        for i in ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
        if i.key == "value"
    ]
    assert len(value) == 1
    assert "€1.0m" in value[0].render("en") and "not a transfer fee" in value[0].render("en")

    row["value_ratio"] = 1.0
    assert not [
        i
        for i in ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
        if i.key == "value"
    ]
    row["value_ratio"], row["market_value_stale"] = 0.25, True
    assert not [
        i
        for i in ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
        if i.key == "value"
    ]


def test_percentile_columns_missing_are_skipped(ranked: pd.DataFrame) -> None:
    row = _best_forward(ranked).drop(labels=["goals_p90" + PCT_SUFFIX])
    out = ins.player_insights(row, confidence_minutes=CONF_MIN, min_minutes=900)
    assert all(i.evidence.get("metric") != "goals_p90" for i in out)


# --- market insights ---------------------------------------------------------------------------


def test_market_insights(ps: pd.DataFrame) -> None:
    strength = pd.DataFrame(
        {
            "competition_id": ["AA1", "BB1"],
            "season": [2025, 2025],
            "clubs": [10, 10],
            "avg_squad_value": [5e7, 3e7],
            "strength_index": [100.0, 60.0],
        }
    )
    out = ins.market_insights(
        ps,
        strength,
        competition_id="BB1",
        competition_name="League B",
        season=2025,
        min_minutes=900,
    )
    keys = [i.key for i in out]
    assert keys == ["league_size", "young_minutes", "league_rank"]
    assert all(i.kind == "observation" for i in out)
    assert "ranks 2 of 2" in out[2].render("en")
    regulars = ps[(ps["competition_id"] == "BB1") & (ps["minutes"] >= 900)]
    assert out[0].evidence["players"] == len(regulars)


def test_market_insights_empty_league(ps: pd.DataFrame) -> None:
    assert (
        ins.market_insights(
            ps,
            pd.DataFrame(columns=["competition_id", "season"]),
            competition_id="ZZ9",
            competition_name="None",
            season=2025,
            min_minutes=900,
        )
        == []
    )


def test_sort_insights_puts_observations_then_confident_first() -> None:
    a = ins.Insight("a", {"en": "", "pt": ""}, "low")
    b = ins.Insight("b", {"en": "", "pt": ""}, "high")
    c = ins.Insight("c", {"en": "", "pt": ""}, "medium", kind="observation")
    assert [i.key for i in ins.sort_insights([a, b, c])] == ["c", "b", "a"]


def test_weakness_never_says_worse_than_100_percent() -> None:
    from scouting.insights import _weakness

    row = pd.Series({"position_group": "Defender", "plus_minus_on_p90": -1.7})
    worst = _weakness(row, "plus_minus_on_p90", 0.0, "medium", 1530, 711)
    assert "worse than 99% of defenders" in worst.render("en")
    assert "pior que 99% dos defesas" in worst.render("pt")
    assert "worse than 80%" in _weakness(row, "plus_minus_on_p90", 20.0, "high", 3000, 711).render(
        "en"
    )
