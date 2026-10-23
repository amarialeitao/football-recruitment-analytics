"""Shared table columns: one format and one plain-language explanation per kind of number.

Every table in the app uses these, so the same number always looks the same (€2.5M, not
€2,500,000 on one page and €2.5m on another) and hovering a column header explains it.
Shares are passed to the table as 0-100 (see :func:`as_percent`) so they show as "94%".
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import streamlit as st

HELP: dict[str, dict[str, str]] = {
    "market_value": {
        "en": "Transfermarkt crowd estimate at the end of the season, not a transfer fee. "
        "2.5M = €2.5 million.",
        "pt": "Estimativa do Transfermarkt no fim da época, não um valor de transferência. "
        "2.5M = 2,5 milhões de euros.",
    },
    "expected_value": {
        "en": "What players with similar output, age and league are usually valued at "
        "(model estimate).",
        "pt": "Valor habitual de jogadores com produção, idade e liga semelhantes "
        "(estimativa do modelo).",
    },
    "value_ratio": {
        "en": "Market value ÷ expected value. Below 1.00x = cheaper than similar players; "
        "0.50x = half the usual price.",
        "pt": "Valor de mercado ÷ valor esperado. Abaixo de 1,00x = mais barato do que jogadores "
        "semelhantes; 0,50x = metade do preço habitual.",
    },
    "performance_score": {
        "en": "Average of the player's percentiles for his position, 0-100. 50 = a typical "
        "regular in the eight leagues.",
        "pt": "Média dos percentis do jogador para a sua posição, 0-100. 50 = um titular típico "
        "nas oito ligas.",
    },
    "minutes_share": {
        "en": "Share of all the league minutes his team played that he was on the pitch.",
        "pt": "Parte dos minutos de liga da equipa em que esteve em campo.",
    },
    "goal_contributions_p90": {
        "en": "Goals plus assists per 90 minutes played.",
        "pt": "Golos mais assistências por 90 minutos jogados.",
    },
    "plus_minus_on_p90": {
        "en": "Goals his team scored minus conceded per 90 minutes while he was on the pitch. "
        "Reflects the team as much as the player.",
        "pt": "Golos marcados menos sofridos pela equipa, por 90 minutos, com ele em campo. "
        "Reflete a equipa tanto quanto o jogador.",
    },
    "similarity": {
        "en": "How close his statistical profile is to the reference player: 100 = identical; "
        "a typical pair of players scores about 30.",
        "pt": "Quão próximo é o perfil estatístico do jogador de referência: 100 = idêntico; "
        "um par típico de jogadores fica perto de 30.",
    },
    "minutes_for_age": {
        "en": "Percentile of share of team minutes among regulars of the same age and position "
        "(100 = plays the most for his age).",
        "pt": "Percentil da % dos minutos da equipa entre titulares da mesma idade e posição "
        "(100 = o que mais joga para a idade).",
    },
    "starts_for_age": {
        "en": "Percentile of start rate among regulars of the same age and position.",
        "pt": "Percentil da % de titularidades entre titulares da mesma idade e posição.",
    },
    "value_growth": {
        "en": "Change in market value between the start and the end of the season.",
        "pt": "Variação do valor de mercado entre o início e o fim da época.",
    },
    "signals": {
        "en": "How many of the three potential signals are strong (0-3).",
        "pt": "Quantos dos três sinais de potencial são fortes (0-3).",
    },
    "strength_index": {
        "en": "Average club squad value relative to Liga Portugal (= 100): a rough measure of "
        "league level.",
        "pt": "Valor médio dos plantéis relativo à Liga Portugal (= 100): uma medida aproximada "
        "do nível da liga.",
    },
    "squad_value": {
        "en": "Average total market value of a club's squad in this league.",
        "pt": "Valor de mercado total médio do plantel de um clube nesta liga.",
    },
    "eu_ppg": {
        "en": "Points per game in Champions League games against clubs from other leagues. "
        "Few games: read with care.",
        "pt": "Pontos por jogo na Liga dos Campeões contra clubes de outras ligas. Poucos jogos: "
        "ler com cuidado.",
    },
    "confidence": {
        "en": "How much evidence is behind the numbers, from minutes played: high from "
        "{high:,} minutes, medium from {medium:,}.",
        "pt": "Quanta evidência suporta os números, pelos minutos jogados: alta a partir de "
        "{high:,} minutos, média a partir de {medium:,}.",
    },
}


def help_text(key: str, lang: str, **values: object) -> str:
    text = HELP[key]["pt" if lang == "pt" else "en"]
    return text.format(**values) if values else text


def money(key: str, lang: str, label: str) -> st.column_config.NumberColumn:
    """Euro amounts in compact form (2.5M, 850K); the header says it is in euros."""
    return st.column_config.NumberColumn(
        label=f"{label} (€)", format="compact", help=help_text(key, lang)
    )


def share(key: str, lang: str) -> st.column_config.ProgressColumn:
    """A 0-100 share as a bar with a whole-number percentage."""
    return st.column_config.ProgressColumn(
        format="%.0f%%", min_value=0, max_value=100, help=help_text(key, lang)
    )


def as_percent(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Copy of ``df`` with 0-1 shares turned into 0-100 (for :func:`share`)."""
    out = df.copy()
    for column in columns:
        out[column] = out[column].astype("float64") * 100
    return out


def number(key: str, lang: str, fmt: str) -> st.column_config.NumberColumn:
    return st.column_config.NumberColumn(format=fmt, help=help_text(key, lang))


def text(key: str, lang: str, **values: object) -> st.column_config.TextColumn:
    return st.column_config.TextColumn(help=help_text(key, lang, **values))
