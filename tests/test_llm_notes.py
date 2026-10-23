"""AI Scouting Notes tests. No network: the model is replaced by fakes. Data is invented."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from scouting.config import LLMSettings, load_settings
from scouting.insights import Insight
from scouting.llm_notes import (
    LLMUnavailableError,
    build_facts,
    build_messages,
    check_numbers,
    generate_note,
    is_available,
    unavailable_reason,
)
from scouting.metrics.percentiles import percentile_ranks

ON = LLMSettings(enabled=True)
KEY = {"ANTHROPIC_API_KEY": "test-key"}


@pytest.fixture
def row(ps: pd.DataFrame) -> pd.Series:
    ranked = percentile_ranks(ps, min_minutes=900)
    out = ranked[(ranked["position_group"] == "Forward") & (ranked["minutes"] >= 900)].iloc[0]
    return out.copy()


@pytest.fixture
def facts(row: pd.Series) -> dict:
    row["name"], row["club_name"], row["competition_name"] = "Player A", "Club A", "League A"
    row["sub_position"], row["games"], row["starts"] = "Centre-Forward", 30, 25
    insight = Insight("k", {"en": "Top 10% of forwards.", "pt": "x"}, "high")
    return build_facts(row, confidence="high", insights=[insight], league_strength_index=100.0)


# --- availability ------------------------------------------------------------------------------


def test_disabled_by_default_in_project_config() -> None:
    settings = load_settings()
    assert settings.llm.enabled is False
    assert not is_available(settings.llm, KEY)


def test_unavailable_reasons() -> None:
    assert "disabled" in unavailable_reason(LLMSettings(), KEY)
    assert "ANTHROPIC_API_KEY" in unavailable_reason(ON, {})


def test_available_when_configured_and_installed() -> None:
    pytest.importorskip("anthropic")  # only with the optional [llm] extra
    assert unavailable_reason(ON, KEY) is None


def test_missing_optional_dependency_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert "[llm]" in unavailable_reason(ON, KEY)


def test_api_key_env_name_is_validated() -> None:
    with pytest.raises(ValueError):
        LLMSettings(api_key_env="sk-not-a-variable-name")


# --- facts and prompt --------------------------------------------------------------------------


def test_facts_contain_only_computed_fields(facts: dict) -> None:
    assert facts["player"] == "Player A"
    assert facts["confidence"] == "high"
    assert facts["league_strength_index"] == 100.0
    assert "Goals per 90" in facts["metrics"]
    assert set(facts["metrics"]["Goals per 90"]) == {"value", "percentile"}
    assert facts["missing_metrics"]
    json.dumps(facts)  # serializable, no numpy or pandas objects


def test_messages_carry_rules_language_and_facts(facts: dict) -> None:
    system, messages = build_messages(facts, "pt")
    assert "European Portuguese" in system
    assert "Use ONLY the facts" in system
    assert messages[0]["role"] == "user"
    assert json.loads(messages[0]["content"].split("\n", 1)[1]) == facts


# --- number check ------------------------------------------------------------------------------


def test_numbers_traceable_to_facts_pass(facts: dict) -> None:
    pct = facts["metrics"]["Goals per 90"]["percentile"]
    text = (
        f"In {facts['minutes']} minutes he ranks in the top {round(100 - pct)}% of forwards "
        f"(percentile {pct:.0f}), per 90 minutes."
    )
    assert check_numbers(text, facts, "en") == []


def test_invented_numbers_are_flagged(facts: dict) -> None:
    assert "37" in check_numbers("He scored 37 goals last season.", facts, "en")


def test_portuguese_decimal_comma(facts: dict) -> None:
    age = facts["age"]
    assert check_numbers(f"Tem {str(age).replace('.', ',')} anos.", facts, "pt") == []


# --- generation --------------------------------------------------------------------------------


def test_generate_with_fake_model(facts: dict) -> None:
    calls = []

    def fake(system, messages, model, max_tokens):
        calls.append((model, max_tokens))
        return f"Played {facts['minutes']} minutes. Scored 37 goals."

    note = generate_note(facts, "en", ON, generate=fake)
    assert calls == [(ON.model, ON.max_tokens)]
    assert note.text.startswith("Played")
    assert note.warnings == ["Number not found in the metrics: 37"]


def test_generate_refuses_when_unavailable(facts: dict) -> None:
    with pytest.raises(LLMUnavailableError, match="disabled"):
        generate_note(facts, "en", LLMSettings(), env=KEY)


# --- page integration --------------------------------------------------------------------------


def _profile_gallery() -> None:
    import os

    import streamlit as st

    from metric_data import synthetic_player_season
    from scouting.config import load_settings
    from scouting.metrics.percentiles import percentile_ranks
    from scouting.ui.ai_note import ai_note_block

    settings = load_settings()
    if os.environ.get("TEST_LLM_ON"):
        settings = settings.model_copy(
            update={"llm": settings.llm.model_copy(update={"enabled": True})}
        )
    row = percentile_ranks(synthetic_player_season(), min_minutes=0).iloc[0].copy()
    row["name"], row["club_name"], row["competition_name"] = "P", "C", "L"
    ai_note_block(row, settings=settings, lang="en", confidence="high", insights=[])
    st.write("end")


def test_block_hidden_when_disabled() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_profile_gallery, default_timeout=30)
    at.run()
    assert not at.exception
    assert not at.button


def test_block_shows_button_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamlit.testing.v1 import AppTest

    pytest.importorskip("anthropic")
    monkeypatch.setenv("TEST_LLM_ON", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    at = AppTest.from_function(_profile_gallery, default_timeout=30)
    at.run()
    assert not at.exception
    assert at.button[0].label == "Generate note"


def test_transformations_depend_on_field_kind() -> None:
    facts = {"minutes": 1, "metrics": {"m": {"value": 0.25, "percentile": 92}}, "x_eur": 1.2e6}
    assert check_numbers("top 8% · 25% · €1.2m", facts, "en") == []
    # 100 - 1 = 99 is only valid for percentiles, not for minutes.
    assert check_numbers("99 minutes", facts, "en") == ["99"]
