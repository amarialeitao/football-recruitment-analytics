"""Status board: OK / ATTENTION per area, each with a plain-language justification.

The status of each area comes from numbers already computed in :mod:`scouting.quality` and
from thresholds declared in ``config/settings.yaml`` (``quality`` and ``analysis`` sections).
No threshold is invented here. Every item carries a text label and a justification, so the
board never depends on colour alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from scouting.config import Analysis, Quality
from scouting.insights import format_decimal, format_int
from scouting.quality import FIELD_LABELS, QualitySummary

Status = Literal["ok", "attention"]
STATUS_LABEL = {
    "en": {"ok": "OK", "attention": "Attention"},
    "pt": {"ok": "OK", "attention": "Atenção"},
}


@dataclass(frozen=True)
class StatusItem:
    area: dict[str, str]
    status: Status
    reason: dict[str, str]


def _pct(value: float, lang: str) -> str:
    return format_decimal(value * 100, lang, 1) + "%"  # type: ignore[arg-type]


def status_board(
    summary: QualitySummary,
    *,
    quality: Quality,
    analysis: Analysis,
    today: pd.Timestamp,
) -> list[StatusItem]:
    """Return one :class:`StatusItem` per area, in a fixed order."""
    items: list[StatusItem] = []

    # Freshness: days between the last game in the data and today.
    age = int((today.normalize() - summary.data_cutoff.normalize()).days)
    cutoff = summary.data_cutoff.date().isoformat()
    fresh = age <= quality.max_data_age_days
    items.append(
        StatusItem(
            area={"en": "Data freshness", "pt": "Atualidade dos dados"},
            status="ok" if fresh else "attention",
            reason={
                "en": f"Last game in the data: {cutoff} ({age} days ago). "
                + ("" if fresh else "Recent transfers and current squads are not reflected."),
                "pt": f"Último jogo nos dados: {cutoff} (há {age} dias). "
                + ("" if fresh else "Transferências recentes e plantéis atuais não aparecem."),
            },
        )
    )

    # Completeness of key fields.
    field, rate = summary.completeness_min
    label = FIELD_LABELS.get(field, {"en": field, "pt": field})
    complete = rate >= quality.completeness_min
    items.append(
        StatusItem(
            area={"en": "Profile completeness", "pt": "Completude dos perfis"},
            status="ok" if complete else "attention",
            reason={
                "en": f"Least complete key field: {label['en']} ({_pct(rate, 'en')} filled; "
                f"threshold {_pct(quality.completeness_min, 'en')}).",
                "pt": f"Campo-chave menos completo: {label['pt']} ({_pct(rate, 'pt')} preenchido; "
                f"limite {_pct(quality.completeness_min, 'pt')}).",
            },
        )
    )

    # Event consistency: games whose goal events do not match the score.
    share = summary.unreconciled_share
    consistent = share <= quality.max_unreconciled_share and summary.duplicate_keys == 0
    items.append(
        StatusItem(
            area={"en": "Match events", "pt": "Eventos dos jogos"},
            status="ok" if consistent else "attention",
            reason={
                "en": f"{summary.unreconciled_games} of {format_int(summary.games)} games "
                "have goal events that do not match the score; their on-pitch goals are left "
                "empty. "
                f"Duplicate player-season rows: {summary.duplicate_keys}.",
                "pt": f"{summary.unreconciled_games} de {format_int(summary.games, 'pt')} "
                "jogos têm eventos de golo que não batem com o placar; os golos em campo ficam "
                "vazios. "
                f"Linhas duplicadas jogador-época: {summary.duplicate_keys}.",
            },
        )
    )

    # Market values.
    stale = summary.stale_value_share
    values_ok = stale <= quality.max_stale_value_share
    items.append(
        StatusItem(
            area={"en": "Market values", "pt": "Valores de mercado"},
            status="ok" if values_ok else "attention",
            reason={
                "en": f"{_pct(stale, 'en')} of regulars have a market value older than a year "
                "(excluded from the Value Finder).",
                "pt": f"{_pct(stale, 'pt')} dos titulares habituais têm valor de mercado com mais "
                "de um ano (excluídos do Value Finder).",
            },
        )
    )

    # Comparison sample: the smallest peer group behind any percentile.
    smallest = summary.smallest_comparison_group
    samples_ok = smallest is not None and smallest >= analysis.confidence_sample.high
    shown = "—" if smallest is None else str(smallest)
    items.append(
        StatusItem(
            area={"en": "Comparison groups", "pt": "Grupos de comparação"},
            status="ok" if samples_ok else "attention",
            reason={
                "en": f"Smallest peer group behind a percentile: {shown} players "
                f"(high confidence from {analysis.confidence_sample.high}).",
                "pt": f"Menor grupo de comparação de um percentil: {shown} jogadores "
                f"(confiança alta a partir de {analysis.confidence_sample.high}).",
            },
        )
    )
    return items
