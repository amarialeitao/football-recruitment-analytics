"""Market Overview (home): the focus league in numbers and where to start looking."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scouting.health import status_board
from scouting.insights import market_insights
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label
from scouting.ui.players import PAGES, money, next_contract_deadline, season_label, tr
from scouting.ui.theme import ACCENT, NEUTRAL_SERIES

TEXT = {
    "cards_scope": {
        "en": "**{league}, {season}, regulars only.** A regular is a player with at least {min} "
        "league minutes (about {games} full games). These four numbers follow the Season filter "
        "only.",
        "pt": "**{league}, {season}, só titulares habituais.** Titular habitual é um jogador com "
        "pelo menos {min} minutos de liga (cerca de {games} jogos completos). Estes quatro números "
        "só seguem o filtro Época.",
    },
    "k_regulars": {"en": "regulars in the league", "pt": "titulares habituais na liga"},
    "k_regulars_note": {
        "en": "players with enough minutes to judge",
        "pt": "jogadores com minutos suficientes para avaliar",
    },
    "k_age": {"en": "typical age of a regular", "pt": "idade típica de um titular"},
    "k_age_note": {
        "en": "median: half are younger, half older",
        "pt": "mediana: metade é mais nova, metade mais velha",
    },
    "k_value": {
        "en": "typical market value of a regular",
        "pt": "valor de mercado típico de um titular",
    },
    "k_value_note": {
        "en": "median, end of season (Transfermarkt estimate, not a fee)",
        "pt": "mediana, fim da época (estimativa Transfermarkt, não é uma transferência)",
    },
    "k_u23": {
        "en": "of regulars' minutes were played by under-23s",
        "pt": "dos minutos dos titulares foram jogados por sub-23",
    },
    "k_u23_note": {
        "en": "{n} young regulars: how much the league trusts youth",
        "pt": "{n} titulares jovens: quanto a liga aposta na juventude",
    },
    "title": {"en": "Market Overview", "pt": "Visão geral do mercado"},
    "question": {
        "en": "How does {league} compare, and where should we start looking?",
        "pt": "Como se compara a {league}, e por onde começar a procurar?",
    },
    "strength_how": {
        "en": "Average club squad value in each league, relative to {league} (= 100). It is a "
        "proxy for financial strength, used as context next to percentiles; see Data Quality "
        "for the European results behind it.",
        "pt": "Valor médio dos plantéis de cada liga, relativo à {league} (= 100). É um indicador "
        "de força financeira, usado como contexto junto dos percentis; veja Qualidade dos dados "
        "para os resultados europeus que o apoiam.",
    },
    "index": {"en": "Strength index", "pt": "Índice de força"},
    "value_title": {
        "en": "{league} has the highest share of regulars valued at half or less of what "
        "their output usually costs ({share:.0%})",
        "pt": "A {league} tem a maior fração de titulares avaliados em metade ou menos do que "
        "a sua produção costuma custar ({share:.0%})",
    },
    "value_how": {
        "en": "Share of each league's regulars whose market value is at most 50% of the value "
        "expected for their output, age and league (see Value Finder for the method). A high "
        "share points to a market where value may be easier to find.",
        "pt": "Fração dos titulares de cada liga cujo valor de mercado é no máximo 50% do valor "
        "esperado para a produção, idade e liga (método no Valor de mercado). Uma fração alta "
        "aponta para um mercado onde pode ser mais fácil encontrar valor.",
    },
    "share_axis": {"en": "Share of regulars", "pt": "Fração dos titulares"},
    "where": {"en": "Where to start in {league}", "pt": "Por onde começar na {league}"},
    "tab_young": {"en": "Young regulars", "pt": "Jovens titulares"},
    "tab_value": {"en": "Valued below output", "pt": "Abaixo do valor esperado"},
    "tab_contract": {"en": "Contracts ending by {date}", "pt": "Contratos até {date}"},
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "score": {"en": "Performance score", "pt": "Índice de rendimento"},
    "ratio": {"en": "Value vs expected", "pt": "Valor vs esperado"},
    "contract": {"en": "Contract end", "pt": "Fim de contrato"},
    "share": {"en": "Share of team minutes", "pt": "% dos minutos da equipa"},
    "guide_title": {
        "en": "New here? How to use this app (2 minutes)",
        "pt": "Primeira visita? Como usar a aplicação (2 minutos)",
    },
    "guide_intro": {
        "en": "The pages follow a scouting workflow. The sidebar filters (season, leagues, "
        "positions, age, minutes, budget) apply everywhere.",
        "pt": "As páginas seguem o fluxo de trabalho de scouting. Os filtros da barra lateral "
        "(época, ligas, posições, idade, minutos, orçamento) aplicam-se a todas.",
    },
    "guide_steps": {
        "en": [
            ("finder", "**Find** players who fit the brief and your budget."),
            (
                "profile",
                "**Profile** one player: what he brings against his peers, how it "
                "changed since last season, and how sure we can be.",
            ),
            ("similar", "**Replace** a player who is leaving: who plays a similar role."),
            ("value", "**Spot value**: players valued low for their output, age and league."),
            ("potential", "**Look young**: under-23s already trusted by their coaches."),
            (
                "shortlist",
                "**Shortlist and compare**: add players from any page, compare three "
                "side by side, then download a one-page report from the profile to share.",
            ),
        ],
        "pt": [
            ("finder", "**Encontrar** jogadores que cumprem o perfil e o orçamento."),
            (
                "profile",
                "**Analisar** um jogador: o que traz face aos pares, como mudou desde "
                "a época anterior e quão certos podemos estar.",
            ),
            ("similar", "**Substituir** um jogador que sai: quem tem um papel parecido."),
            ("value", "**Encontrar valor**: jogadores avaliados abaixo da produção, idade e liga."),
            ("potential", "**Olhar para jovens**: sub-23 que já têm a confiança do treinador."),
            (
                "shortlist",
                "**Lista e comparação**: adicione jogadores de qualquer página, "
                "compare três lado a lado e descarregue o relatório de uma página no perfil.",
            ),
        ],
    },
    "guide_pages": {
        "finder": {"en": "Player Finder", "pt": "Pesquisa"},
        "profile": {"en": "Player Profile", "pt": "Perfil"},
        "similar": {"en": "Similar Players", "pt": "Parecidos"},
        "value": {"en": "Value Finder", "pt": "Valor"},
        "potential": {"en": "Potential", "pt": "Potencial"},
        "shortlist": {"en": "Shortlist", "pt": "Lista"},
    },
    "guide_tips": {
        "en": "Every chart has a *How to read this chart* button, hovering a column header "
        "explains it, every finding shows how much evidence is behind it (high, medium or low "
        "confidence), and the **Glossary** at the bottom of the sidebar explains the terms.",
        "pt": "Cada gráfico tem um botão *Como ler este gráfico*, passar o rato pelo cabeçalho "
        "de uma coluna explica-a, cada conclusão mostra quanta evidência a suporta (confiança "
        "alta, média ou baixa), e o **Glossário** no fundo da barra lateral explica os termos.",
    },
    "links": {
        "finder": {"en": "Find players", "pt": "Pesquisar jogadores"},
        "value": {"en": "Value Finder", "pt": "Valor de mercado"},
        "potential": {"en": "Young players", "pt": "Jovens"},
        "quality": {"en": "Data quality", "pt": "Qualidade dos dados"},
    },
}

TOP_N = 8

settings, data = setup_page("Football Recruitment Analytics")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)

focus = settings.scope.focus_competition
focus_name = settings.scope.competitions[focus]
min_minutes = settings.analysis.min_minutes
season = filters.season
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang).format(league=focus_name))

with st.expander(tr(TEXT["guide_title"], lang), icon=":material/explore:"):
    st.markdown(tr(TEXT["guide_intro"], lang))
    for step, (page_key, text) in enumerate(TEXT["guide_steps"][lang], start=1):
        text_col, link_col = st.columns([4, 1])
        text_col.markdown(f"{step}. {text}")
        link_col.page_link(PAGES[page_key], label=f"{tr(TEXT['guide_pages'][page_key], lang)} →")
    st.caption(tr(TEXT["guide_tips"], lang))

league = universe[universe["competition_id"] == focus]
regulars = league[league["minutes"] >= min_minutes]
u23_share = (
    regulars.loc[regulars["age"] < 23, "minutes"].sum() / regulars["minutes"].sum()
    if not regulars.empty
    else float("nan")
)
n_young = int((regulars["age"] < 23).sum())
st.markdown(
    tr(TEXT["cards_scope"], lang).format(
        league=focus_name,
        season=season_label(season),
        min=num(min_minutes, lang),
        games=num(min_minutes / 90, lang),
    )
)
c.kpi_row(
    [
        c.Kpi(
            num(len(regulars), lang),
            tr(TEXT["k_regulars"], lang),
            tr(TEXT["k_regulars_note"], lang),
        ),
        c.Kpi(
            num(regulars["age"].median(), lang, 1),
            tr(TEXT["k_age"], lang),
            tr(TEXT["k_age_note"], lang),
        ),
        c.Kpi(
            money(regulars["market_value_end"].median(), lang),
            tr(TEXT["k_value"], lang),
            tr(TEXT["k_value_note"], lang),
        ),
        c.Kpi(
            f"{u23_share:.0%}",
            tr(TEXT["k_u23"], lang),
            tr(TEXT["k_u23_note"], lang).format(n=num(n_young, lang)),
        ),
    ]
)

insights = market_insights(
    data.players,
    data.league_strength,
    competition_id=focus,
    competition_name=focus_name,
    season=season,
    min_minutes=min_minutes,
    sample_thresholds=(
        settings.analysis.confidence_sample.medium,
        settings.analysis.confidence_sample.high,
    ),
)
rank = next((i for i in insights if i.key == "league_rank"), None)
footer = c.source_note(lang, data_cutoff=data.data_cutoff, season_label=season_label(season))

# League strength
strength = data.league_strength[data.league_strength["season"] == season].sort_values(
    "strength_index"
)
fig = go.Figure(
    go.Bar(
        x=strength["strength_index"],
        y=strength["competition_name"],
        orientation="h",
        marker={
            "color": [
                ACCENT if c_id == focus else NEUTRAL_SERIES for c_id in strength["competition_id"]
            ]
        },
        text=[f"{v:.0f}" for v in strength["strength_index"]],
        textposition="outside",
        hovertemplate="%{y}<br>Index %{x:.0f}<extra></extra>",
    )
)
fig.update_layout(
    title=rank.title(lang) if rank else tr(TEXT["index"], lang),
    xaxis={"title": tr(TEXT["index"], lang), "rangemode": "tozero"},
    yaxis={"title": None},
    height=380,
)
c.chart_block(
    fig,
    lang=lang,
    footer=footer,
    how_to_read=tr(TEXT["strength_how"], lang).format(league=focus_name),
    insights=insights,
    key="strength",
)

# Where the value is
season_regulars = universe[
    (universe["minutes"] >= min_minutes)
    & universe["value_ratio"].notna()
    & ~universe["market_value_stale"].fillna(True).astype(bool)
]
by_league = (
    season_regulars.assign(cheap=season_regulars["value_ratio"] <= 0.5)
    .groupby("competition_name")
    .agg(share=("cheap", "mean"), n=("cheap", "size"))
    .sort_values("share")
    .reset_index()
)
if not by_league.empty:
    top = by_league.iloc[-1]
    fig = go.Figure(
        go.Bar(
            x=by_league["share"],
            y=by_league["competition_name"],
            orientation="h",
            marker={
                "color": [
                    ACCENT if name == focus_name else NEUTRAL_SERIES
                    for name in by_league["competition_name"]
                ]
            },
            text=[f"{s:.0%}" for s in by_league["share"]],
            textposition="outside",
            customdata=by_league["n"],
            hovertemplate="%{y}<br>%{x:.0%} of %{customdata} regulars<extra></extra>",
        )
    )
    fig.update_layout(
        title=tr(TEXT["value_title"], lang).format(
            league=top["competition_name"], share=top["share"]
        ),
        xaxis={"title": tr(TEXT["share_axis"], lang), "tickformat": ".0%", "rangemode": "tozero"},
        yaxis={"title": None},
        height=380,
    )
    c.chart_block(
        fig,
        lang=lang,
        footer=footer,
        how_to_read=tr(TEXT["value_how"], lang),
        key="value_share",
    )

# Where to start in the focus league
st.subheader(tr(TEXT["where"], lang).format(league=focus_name))
deadline = next_contract_deadline(data.data_cutoff)
tabs = st.tabs(
    [
        tr(TEXT["tab_young"], lang),
        tr(TEXT["tab_value"], lang),
        tr(TEXT["tab_contract"], lang).format(date=deadline.date().isoformat()),
    ]
)


def _table(df: pd.DataFrame, extra: dict[str, pd.Series]) -> pd.DataFrame:
    base = {
        tr(TEXT["name"], lang): df["name"],
        tr(TEXT["club"], lang): df["club_name"],
        tr(TEXT["position"], lang): df["sub_position"].map(lambda p: position_label(p, lang)),
        tr(TEXT["age"], lang): df["age"],
        tr(TEXT["minutes"], lang): df["minutes"],
    }
    return pd.DataFrame({**base, **extra}).reset_index(drop=True)


money_col = col.money("market_value", lang, tr(TEXT["value"], lang))
age_col = st.column_config.NumberColumn(format="%.1f")
score_col = col.number("performance_score", lang, "%.0f")
share_name = tr(TEXT["share"], lang)
young = regulars[regulars["age"] < 23].sort_values("minutes_share", ascending=False).head(TOP_N)
tabs[0].dataframe(
    col.as_percent(
        _table(
            young,
            {
                share_name: young["minutes_share"],
                tr(TEXT["value"], lang): young["market_value_end"],
            },
        ),
        [share_name],
    ),
    hide_index=True,
    width="stretch",
    column_config={
        tr(TEXT["age"], lang): age_col,
        tr(TEXT["value"], lang): money_col,
        share_name: col.share("minutes_share", lang),
    },
)
cheap = (
    regulars[regulars["value_ratio"].notna() & ~regulars["market_value_stale"].astype(bool)]
    .sort_values("value_ratio")
    .head(TOP_N)
)
tabs[1].dataframe(
    _table(
        cheap,
        {
            tr(TEXT["score"], lang): cheap["performance_score"],
            tr(TEXT["value"], lang): cheap["market_value_end"],
            tr(TEXT["ratio"], lang): cheap["value_ratio"],
        },
    ),
    hide_index=True,
    width="stretch",
    column_config={
        tr(TEXT["age"], lang): age_col,
        tr(TEXT["value"], lang): money_col,
        tr(TEXT["score"], lang): score_col,
        tr(TEXT["ratio"], lang): col.number("value_ratio", lang, "%.2fx"),
    },
)
ending = (
    regulars[regulars["contract_expiration_date"] <= deadline]
    .sort_values("performance_score", ascending=False)
    .head(TOP_N)
)
tabs[2].dataframe(
    _table(
        ending,
        {
            tr(TEXT["contract"], lang): ending["contract_expiration_date"].dt.date,
            tr(TEXT["score"], lang): ending["performance_score"],
            tr(TEXT["value"], lang): ending["market_value_end"],
        },
    ),
    hide_index=True,
    width="stretch",
    column_config={
        tr(TEXT["age"], lang): age_col,
        tr(TEXT["value"], lang): money_col,
        tr(TEXT["score"], lang): score_col,
    },
)

link_cols = st.columns(4)
for link_col, key in zip(link_cols, ["finder", "value", "potential", "quality"], strict=True):
    link_col.page_link(PAGES[key], label=f"{tr(TEXT['links'][key], lang)} →")

c.status_board(
    status_board(
        data.quality,
        quality=settings.quality,
        analysis=settings.analysis,
        today=pd.Timestamp.today().normalize(),
    ),
    lang,
)
