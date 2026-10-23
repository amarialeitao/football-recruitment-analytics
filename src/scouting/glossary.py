"""The glossary: every term the app uses, explained once, in plain words and both languages.

The app shows it in the sidebar of every page, and README.md has the same list (a test checks
that every English term here appears there). Numbers that come from the configuration
(minimum minutes, confidence thresholds) are filled in from the settings, so the text never
disagrees with what the app does.
"""

from __future__ import annotations

from dataclasses import dataclass

from scouting.config import Settings


@dataclass(frozen=True)
class Term:
    term: dict[str, str]
    text: dict[str, str]


GLOSSARY: tuple[Term, ...] = (
    Term(
        {"en": "Regular", "pt": "Titular habitual"},
        {
            "en": "A player with at least {min} league minutes in the season (about {games} full "
            "games). Only regulars are compared, because a few good games prove little.",
            "pt": "Jogador com pelo menos {min} minutos de liga na época (cerca de {games} jogos "
            "completos). Só os titulares habituais são comparados: poucos jogos provam pouco.",
        },
    ),
    Term(
        {"en": "Per 90", "pt": "Por 90"},
        {
            "en": "Per 90 minutes played, so a player with 1,000 minutes and one with 3,000 can be "
            "compared fairly.",
            "pt": "Por 90 minutos jogados, para comparar com justiça um jogador com 1.000 minutos "
            "e outro com 3.000.",
        },
    ),
    Term(
        {"en": "Percentile", "pt": "Percentil"},
        {
            "en": "Where a player ranks among regulars of the same position group in the same "
            "season, across all eight leagues: 90 means better than 90% of them. 100 is always "
            "best, so for cards and goals conceded a high percentile means fewer.",
            "pt": "A posição do jogador entre os titulares do mesmo grupo de posição na mesma "
            "época, nas oito ligas: 90 quer dizer melhor do que 90% deles. 100 é sempre o melhor, "
            "por isso em cartões e golos sofridos um percentil alto quer dizer menos.",
        },
    ),
    Term(
        {"en": "Median", "pt": "Mediana"},
        {
            "en": "The middle value: half the players are above it, half below. Used instead of "
            "the average so a few extreme values do not distort it.",
            "pt": "O valor do meio: metade dos jogadores está acima, metade abaixo. Usada em vez "
            "da média para que valores extremos não a distorçam.",
        },
    ),
    Term(
        {"en": "Share of team minutes", "pt": "% dos minutos da equipa"},
        {
            "en": "The share of all the league minutes his team played that he was on the pitch: "
            "the clearest public sign of how much a coach trusts him.",
            "pt": "A parte dos minutos de liga da equipa em que esteve em campo: o sinal público "
            "mais claro da confiança do treinador.",
        },
    ),
    Term(
        {"en": "On-pitch goal difference", "pt": "Saldo de golos em campo"},
        {
            "en": "Goals his team scored minus goals it conceded while he was on the pitch, per "
            "90 minutes. It reflects the team as much as the player.",
            "pt": "Golos marcados menos golos sofridos pela equipa com ele em campo, por 90 "
            "minutos. Reflete a equipa tanto quanto o jogador.",
        },
    ),
    Term(
        {"en": "Confidence", "pt": "Confiança"},
        {
            "en": "How much evidence is behind a number: high from {high} minutes, medium from "
            "{min}, low below. When several samples are involved, the weakest decides.",
            "pt": "Quanta evidência suporta um número: alta a partir de {high} minutos, média a "
            "partir de {min}, baixa abaixo disso. Com várias amostras, decide a mais fraca.",
        },
    ),
    Term(
        {"en": "Performance score", "pt": "Índice de rendimento"},
        {
            "en": "The average of a player's percentiles for his position, from 0 to 100. 50 is a "
            "typical regular. It measures output and trust with public data, not overall quality.",
            "pt": "A média dos percentis do jogador para a sua posição, de 0 a 100. 50 é um "
            "titular típico. Mede produção e confiança com dados públicos, não a qualidade total.",
        },
    ),
    Term(
        {"en": "Market value", "pt": "Valor de mercado"},
        {
            "en": "Transfermarkt's crowd estimate of what a player is worth. It is not a transfer "
            "fee and can be out of date.",
            "pt": "A estimativa do Transfermarkt sobre quanto vale um jogador. Não é um valor de "
            "transferência e pode estar desatualizada.",
        },
    ),
    Term(
        {"en": "Value vs expected", "pt": "Valor vs esperado"},
        {
            "en": "Market value divided by what players with similar output, age and league are "
            "usually valued at. Below 1.00x is cheaper than usual; 0.50x is half the usual price. "
            "Tested on past seasons: a starting point for scouting, not a prediction.",
            "pt": "Valor de mercado a dividir pelo valor habitual de jogadores com produção, idade "
            "e liga semelhantes. Abaixo de 1,00x é mais barato do que o habitual; 0,50x é metade. "
            "Testado em épocas passadas: um ponto de partida, não uma previsão.",
        },
    ),
    Term(
        {"en": "League level", "pt": "Nível da liga"},
        {
            "en": "The average squad value of a league's clubs, with Liga Portugal = 100. A rough "
            "guide to how big a step a move between leagues is.",
            "pt": "O valor médio dos plantéis dos clubes de uma liga, com a Liga Portugal = 100. "
            "Uma indicação aproximada do salto entre ligas.",
        },
    ),
    Term(
        {"en": "Similarity", "pt": "Similaridade"},
        {
            "en": "How close two players' statistical profiles are, from 0 to 100: 100 is "
            "identical and a typical pair of players scores about 30. Similar role, not "
            "necessarily similar quality.",
            "pt": "Quão próximos são os perfis estatísticos de dois jogadores, de 0 a 100: 100 é "
            "idêntico e um par típico fica perto de 30. Papel semelhante, não necessariamente "
            "qualidade semelhante.",
        },
    ),
    Term(
        {"en": "Potential signals", "pt": "Sinais de potencial"},
        {
            "en": "For players aged {young} or under: plays a lot for his age, starts a lot for "
            "his age, and market value rising. Signals to look closer, not predictions.",
            "pt": "Para jogadores com {young} anos ou menos: joga muito para a idade, é muito "
            "titular para a idade e o valor de mercado sobe. Sinais para olhar com atenção, não "
            "previsões.",
        },
    ),
)


def entries(settings: Settings, lang: str) -> list[tuple[str, str]]:
    """``(term, explanation)`` pairs in ``lang``, with the configured numbers filled in."""
    lang = "pt" if lang == "pt" else "en"
    a = settings.analysis
    sep = "." if lang == "pt" else ","

    def thousands(value: int) -> str:
        return f"{value:,}".replace(",", sep)

    values = {
        "min": thousands(a.min_minutes),
        "games": round(a.min_minutes / 90),
        "high": thousands(a.confidence_minutes.high),
        "young": f"{a.young_age_max:g}",
    }
    return [(t.term[lang], t.text[lang].format(**values)) for t in GLOSSARY]
