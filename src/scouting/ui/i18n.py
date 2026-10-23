"""Interface texts in English and Portuguese.

Every UI string lives in ``TEXTS`` with both languages. ``t(key, lang)`` returns the string;
a missing key raises, so an untranslated label is caught by the tests, not by users.
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["en", "pt"]
LANGUAGES: dict[Lang, str] = {"en": "English", "pt": "Português"}
DEFAULT_LANG: Lang = "en"

TEXTS: dict[str, dict[Lang, str]] = {
    # Sidebar
    "language": {"en": "Language", "pt": "Idioma"},
    "filters": {"en": "Filters", "pt": "Filtros"},
    "season": {"en": "Season", "pt": "Época"},
    "leagues": {"en": "Leagues", "pt": "Ligas"},
    "positions": {"en": "Positions", "pt": "Posições"},
    "age": {"en": "Age", "pt": "Idade"},
    "min_minutes": {"en": "Minimum minutes", "pt": "Mínimo de minutos"},
    "max_value": {"en": "Maximum market value (€m)", "pt": "Valor de mercado máximo (€m)"},
    "no_limit": {"en": "No limit", "pt": "Sem limite"},
    "clear_filters": {"en": "Clear filters", "pt": "Limpar filtros"},
    "players_selected": {"en": "players match the filters", "pt": "jogadores nos filtros"},
    # Common blocks
    "how_to_read": {"en": "How to read this chart", "pt": "Como ler este gráfico"},
    "key_observations": {"en": "Key observations", "pt": "Principais observações"},
    "observed_data": {"en": "Observed data", "pt": "Dados observados"},
    "status_board": {"en": "Data status", "pt": "Estado dos dados"},
    "not_available": {
        "en": "Not available in public data",
        "pt": "Não disponível em dados públicos",
    },
    "not_available_note": {
        "en": "These metrics would matter for this decision, but no open source covers them for "
        "these leagues. They are shown as missing rather than estimated.",
        "pt": "Estas métricas importariam para esta decisão, mas nenhuma fonte aberta as cobre "
        "para estas ligas. Aparecem como em falta em vez de estimadas.",
    },
    "no_data": {
        "en": "No players match the current filters.",
        "pt": "Nenhum jogador corresponde aos filtros atuais.",
    },
    "data_not_ready": {"en": "Data not available", "pt": "Dados indisponíveis"},
    # Positions
    "Forward": {"en": "Forward", "pt": "Avançado"},
    "Midfielder": {"en": "Midfielder", "pt": "Médio"},
    "Defender": {"en": "Defender", "pt": "Defesa"},
    "Goalkeeper": {"en": "Goalkeeper", "pt": "Guarda-redes"},
    # Confidence
    "confidence_high": {"en": "high confidence", "pt": "confiança alta"},
    "confidence_medium": {"en": "medium confidence", "pt": "confiança média"},
    "confidence_low": {"en": "low confidence", "pt": "confiança baixa"},
    # Footer
    "source": {"en": "Source", "pt": "Fonte"},
    "data_to": {"en": "Data to", "pt": "Dados até"},
}


# Detailed positions as published by the source (English), with Portuguese labels.
SUB_POSITIONS_PT: dict[str, str] = {
    "Goalkeeper": "Guarda-redes",
    "Centre-Back": "Defesa central",
    "Left-Back": "Lateral esquerdo",
    "Right-Back": "Lateral direito",
    "Defensive Midfield": "Médio defensivo",
    "Central Midfield": "Médio centro",
    "Attacking Midfield": "Médio ofensivo",
    "Left Midfield": "Médio esquerdo",
    "Right Midfield": "Médio direito",
    "Left Winger": "Extremo esquerdo",
    "Right Winger": "Extremo direito",
    "Second Striker": "Segundo avançado",
    "Centre-Forward": "Ponta de lança",
}


def position_label(position: str | None, lang: Lang) -> str:
    """Detailed position in ``lang``; unknown values are returned as published."""
    if position is None or position != position:  # None or NaN
        return "—"
    return SUB_POSITIONS_PT.get(position, position) if lang == "pt" else position


def num(value: float | None, lang: Lang, digits: int = 0) -> str:
    """Number with the language's separators: 1,906.5 (en) / 1.906,5 (pt)."""
    if value is None or value != value:
        return "—"
    text = f"{value:,.{digits}f}"
    if lang == "pt":
        text = text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return text


def t(key: str, lang: Lang = DEFAULT_LANG) -> str:
    """Translated text for ``key``. Raises ``KeyError`` for unknown keys."""
    try:
        return TEXTS[key][lang]
    except KeyError:
        raise KeyError(f"Missing UI text '{key}' for language '{lang}'") from None
