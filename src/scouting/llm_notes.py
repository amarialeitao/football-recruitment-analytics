"""AI Scouting Notes: a short written profile drafted by an LLM from the computed metrics only.

The feature is **optional and off by default**. It runs only when all three are true:

1. ``llm.enabled: true`` in ``config/settings.yaml``;
2. the API key environment variable (``ANTHROPIC_API_KEY`` by default) is set;
3. the optional dependency is installed (``pip install -e ".[llm]"``).

Safeguards:

* The model receives a JSON of facts built here from the player's row: identity, minutes,
  per-90 values, percentiles, comparison group size, market value and the confidence level.
  Nothing else (no web access, no free text from users).
* The instructions forbid any number, event or opinion not in the facts and require the text to
  state the confidence level and the main data gaps.
* :func:`check_numbers` compares every number in the answer with the facts; numbers that cannot
  be traced are returned as warnings and shown next to the note.
* The UI labels the text as AI-generated.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from scouting.config import LLMSettings
from scouting.insights import Insight
from scouting.metrics.catalog import PROFILE_METRICS, UNAVAILABLE_METRICS, metric
from scouting.metrics.percentiles import PCT_SUFFIX

LANG_NAMES = {"en": "English", "pt": "European Portuguese"}
ALWAYS_ALLOWED_NUMBERS = {90.0}  # "per 90" appears in metric names

SYSTEM_PROMPT = """You are a football scouting analyst writing for a sporting director.
You receive a JSON object with facts about one player-season, computed from public data.

Rules:
- Use ONLY the facts in the JSON. Do not add statistics, events, transfers, injuries, playing
  style, nationality details or opinions that are not supported by a field in the JSON.
- Every number you write must appear in the JSON (you may round it or show a percentile as
  "top X%"). Do not compute new numbers.
- Percentiles compare the player with players of the same position group in the leagues in
  scope; 100 is best (lower-is-better metrics are already inverted).
- State the confidence level given in the JSON and what it is based on.
- End with one sentence on what the data cannot show, using "missing_metrics".
- Market value is an estimate, not a transfer fee: say so if you mention it.
- Write 120 to 180 words in {language}, plain prose, no headings, no bullet points."""


class LLMUnavailableError(RuntimeError):
    """The feature is disabled or not configured; the message says what is missing."""


@dataclass(frozen=True)
class ScoutingNote:
    text: str
    model: str
    lang: str
    generated_at: str
    warnings: list[str] = field(default_factory=list)


# --- availability ------------------------------------------------------------------------------


def unavailable_reason(settings: LLMSettings, env: Mapping[str, str] | None = None) -> str | None:
    """Why the feature cannot run (``None`` when it can)."""
    env = os.environ if env is None else env
    if not settings.enabled:
        return "AI Scouting Notes are disabled (llm.enabled is false in config/settings.yaml)."
    if not env.get(settings.api_key_env):
        return f"Environment variable {settings.api_key_env} is not set."
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return 'The optional dependency is missing: pip install -e ".[llm]"'
    return None


def is_available(settings: LLMSettings, env: Mapping[str, str] | None = None) -> bool:
    return unavailable_reason(settings, env) is None


# --- facts and prompt --------------------------------------------------------------------------


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):  # numpy scalars
        value = value.item()
    if isinstance(value, float):
        return round(value, 2)
    return value


def build_facts(
    row: pd.Series,
    *,
    confidence: str,
    insights: Iterable[Insight] = (),
    league_strength_index: float | None = None,
) -> dict[str, Any]:
    """The only information sent to the model, built from one player-season row."""
    group = row.get("position_group")
    keys = PROFILE_METRICS.get(group, ())
    metrics = {
        metric(k).label: {
            "value": _clean(row.get(k)),
            "percentile": _clean(row.get(k + PCT_SUFFIX)),
        }
        for k in keys
    }
    season = int(row["season"])
    return {
        "player": _clean(row.get("name")),
        "club": _clean(row.get("club_name")),
        "league": _clean(row.get("competition_name")),
        "season": f"{season}/{(season + 1) % 100:02d}",
        "position_group": group,
        "position": _clean(row.get("sub_position")),
        "age": _clean(row.get("age")),
        "minutes": _clean(row.get("minutes")),
        "games": _clean(row.get("games")),
        "starts": _clean(row.get("starts")),
        "confidence": confidence,
        "comparison_group_size": _clean(row.get("comparison_n")),
        "metrics": metrics,
        "market_value_eur": _clean(row.get("market_value_end")),
        "expected_market_value_eur": _clean(row.get("expected_market_value")),
        "league_strength_index": _clean(league_strength_index),
        "contract_until": _clean(row.get("contract_expiration_date")),
        "automatic_findings": [i.render("en") for i in insights],
        "missing_metrics": [m["en"] for m in UNAVAILABLE_METRICS],
    }


def build_messages(facts: Mapping[str, Any], lang: str) -> tuple[str, list[dict[str, str]]]:
    """System prompt and user message for the model."""
    system = SYSTEM_PROMPT.format(language=LANG_NAMES[lang])
    user = "Facts (JSON):\n" + json.dumps(facts, ensure_ascii=False, indent=2)
    return system, [{"role": "user", "content": user}]


# --- output check ------------------------------------------------------------------------------

_NUMBER = re.compile(r"(?<![\w.,])[-+]?\d[\d.,]*")


def _parse_number(token: str, lang: str) -> float | None:
    token = token.strip(".,")
    # Portuguese writes 1.906,5; English writes 1,906.5.
    pt = lang == "pt"
    token = token.replace(".", "").replace(",", ".") if pt else token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def _variants(key: str, value: float) -> set[float]:
    """Ways a fact may legitimately be written, by kind of field."""
    out = {value}
    if key == "percentile":
        out.add(100 - value)  # "top 8%" for percentile 92
    elif key.endswith("_eur"):
        out |= {value / 1e6, value / 1e3}  # "€1.2m", "€850k"
    elif 0 < abs(value) <= 1.5:
        out.add(value * 100)  # shares written as percentages
    return out


def _fact_numbers(facts: Any, key: str = "") -> set[float]:
    found: set[float] = set()
    if isinstance(facts, Mapping):
        for k, value in facts.items():
            found |= _fact_numbers(value, str(k))
    elif isinstance(facts, list | tuple):
        for value in facts:
            found |= _fact_numbers(value, key)
    elif isinstance(facts, bool):
        pass
    elif isinstance(facts, int | float):
        found |= _variants(key, float(facts))
    elif isinstance(facts, str):
        for token in _NUMBER.findall(facts):
            if (number := _parse_number(token, "en")) is not None:
                found.add(number)
    return found


def _traceable(number: float, allowed: set[float]) -> bool:
    candidates = allowed | ALWAYS_ALLOWED_NUMBERS
    # Rounding is allowed: half a unit, or 0.5% for large numbers (2,875 -> "2,870").
    return any(abs(number - v) <= max(0.51, 0.005 * abs(v)) for v in candidates)


def check_numbers(text: str, facts: Mapping[str, Any], lang: str) -> list[str]:
    """Numbers in ``text`` that cannot be traced to ``facts`` (empty list when all are)."""
    allowed = _fact_numbers(facts)
    problems = []
    for token in _NUMBER.findall(text):
        value = _parse_number(token, lang)
        if value is not None and not _traceable(abs(value), allowed):
            problems.append(token)
    return problems


# --- generation --------------------------------------------------------------------------------

Generate = Callable[[str, list[dict[str, str]], str, int], str]


def _anthropic_generate(api_key: str) -> Generate:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def generate(system: str, messages: list[dict[str, str]], model: str, max_tokens: int) -> str:
        response = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages
        )
        return "".join(block.text for block in response.content if block.type == "text")

    return generate


def generate_note(
    facts: Mapping[str, Any],
    lang: str,
    settings: LLMSettings,
    *,
    generate: Generate | None = None,
    env: Mapping[str, str] | None = None,
) -> ScoutingNote:
    """Ask the model for a note and check its numbers against the facts.

    ``generate`` can be injected (tests use a fake); otherwise the Anthropic client is used,
    which requires the feature to be available.
    """
    if generate is None:
        reason = unavailable_reason(settings, env)
        if reason:
            raise LLMUnavailableError(reason)
        env = os.environ if env is None else env
        generate = _anthropic_generate(env[settings.api_key_env])

    system, messages = build_messages(facts, lang)
    text = generate(system, messages, settings.model, settings.max_tokens).strip()
    warnings = [f"Number not found in the metrics: {n}" for n in check_numbers(text, facts, lang)]
    return ScoutingNote(
        text=text,
        model=settings.model,
        lang=lang,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        warnings=warnings,
    )
