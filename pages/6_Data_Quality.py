"""Data Quality: coverage, completeness, league strength evidence and known limitations."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scouting.health import status_board
from scouting.quality import FIELD_LABELS
from scouting.ui import components as c
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector
from scouting.ui.i18n import num
from scouting.ui.players import season_label, tr
from scouting.ui.theme import ATTENTION, CATEGORICAL, MUTED, PRIMARY

TEXT = {
    "title": {"en": "Data Quality", "pt": "Qualidade dos dados"},
    "question": {
        "en": "Can we trust what we are seeing, and what is missing?",
        "pt": "Podemos confiar no que vemos, e o que falta?",
    },
    "cutoff": {"en": "Last game in the data", "pt": "Último jogo nos dados"},
    "games": {"en": "League games", "pt": "Jogos de liga"},
    "rows": {"en": "Player-seasons", "pt": "Jogador-épocas"},
    "version": {"en": "Source version", "pt": "Versão da fonte"},
    "coverage_title": {
        "en": "Regulars ({min}+ minutes) per league and season: {low} has the smallest pool",
        "pt": "Titulares habituais ({min}+ minutos) por liga e época: {low} tem o menor grupo",
    },
    "coverage_how": {
        "en": "Number of players who reached the minimum minutes, per league and season. Smaller "
        "pools make percentiles and models less stable. Only the regular season is covered: "
        "play-off and championship rounds are separate competitions in the source.",
        "pt": "Número de jogadores que atingiram o mínimo de minutos, por liga e época. Grupos "
        "menores tornam percentis e modelos menos estáveis. Só a fase regular está coberta: "
        "play-offs e fases de campeonato são competições separadas na fonte.",
    },
    "players_axis": {"en": "Players", "pt": "Jogadores"},
    "complete_title": {
        "en": "Key profile fields: {field} is the least complete ({rate} filled)",
        "pt": "Campos-chave do perfil: {field} é o menos completo ({rate} preenchido)",
    },
    "complete_how": {
        "en": "Share of player-seasons with each key field filled. The dotted line is the "
        "threshold set in config/settings.yaml. Contract dates are reported separately because "
        "a missing contract is often a real situation (free agent, loan), not bad data.",
        "pt": "Fração de jogador-épocas com cada campo-chave preenchido. A linha pontilhada é o "
        "limite definido em config/settings.yaml. As datas de contrato são reportadas à parte "
        "porque a falta de contrato é muitas vezes real (sem clube, empréstimo), não erro.",
    },
    "contract_note": {
        "en": "Contract date missing for {share:.0%} of player-seasons.",
        "pt": "Data de contrato em falta em {share:.0%} das jogador-épocas.",
    },
    "strength": {"en": "League strength and its evidence", "pt": "Força das ligas e evidência"},
    "strength_note": {
        "en": "Index = average club squad value relative to the focus league (100). European "
        "results are shown as supporting evidence only: the source covers the Champions League "
        "and its qualifying rounds, not the Europa or Conference League.",
        "pt": "Índice = valor médio dos plantéis relativo à liga de foco (100). Os resultados "
        "europeus são só evidência de apoio: a fonte cobre a Liga dos Campeões e a "
        "qualificação, não a Liga Europa nem a Liga Conferência.",
    },
    "league": {"en": "League", "pt": "Liga"},
    "season": {"en": "Season", "pt": "Época"},
    "clubs": {"en": "Clubs", "pt": "Clubes"},
    "squad": {"en": "Avg squad value", "pt": "Valor médio do plantel"},
    "index": {"en": "Strength index", "pt": "Índice de força"},
    "eu_games": {"en": "European games", "pt": "Jogos europeus"},
    "eu_ppg": {"en": "Points per game vs other leagues", "pt": "Pontos por jogo vs outras ligas"},
    "limits": {"en": "Known limitations", "pt": "Limitações conhecidas"},
    "source": {"en": "Source and licence", "pt": "Fonte e licença"},
}

LIMITATIONS = [
    {
        "en": "No event data for these leagues: no xG, passes, defensive actions or duels.",
        "pt": "Sem dados de eventos para estas ligas: sem xG, passes, ações defensivas ou duelos.",
    },
    {
        "en": "The source stopped updating in July 2026: 2026/27 squads and recent transfers are "
        "missing; contract dates are a snapshot.",
        "pt": "A fonte deixou de ser atualizada em julho de 2026: faltam os plantéis de 2026/27 e "
        "as transferências recentes; as datas de contrato são um retrato.",
    },
    {
        "en": "Only the regular season of each league: play-off and championship rounds "
        "(Belgium, Denmark, Greece, Scotland) are not included.",
        "pt": "Só a fase regular de cada liga: play-offs e fases de campeonato (Bélgica, "
        "Dinamarca, Grécia, Escócia) não estão incluídos.",
    },
    {
        "en": "Liga Portugal 2 and LaLiga 2 are not in the open dataset.",
        "pt": "A Liga Portugal 2 e a LaLiga 2 não estão no dataset aberto.",
    },
    {
        "en": "Market value is a crowd estimate, not a transfer fee.",
        "pt": "Valor de mercado é uma estimativa, não um preço de transferência.",
    },
    {
        "en": "On-pitch goal difference reflects the team as much as the player.",
        "pt": "O saldo de golos em campo reflete a equipa tanto quanto o jogador.",
    },
]

settings, data = setup_page("Data Quality")
lang = language_selector()
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))

q = data.quality
version = (data.manifest.get("source_version") or [{}])[0]
version_label = str(version.get("commit_hash") or version.get("version") or "—")[:7]
c.kpi_row(
    [
        c.Kpi(q.data_cutoff.date().isoformat(), tr(TEXT["cutoff"], lang)),
        c.Kpi(num(q.games, lang), tr(TEXT["games"], lang)),
        c.Kpi(num(q.player_seasons, lang), tr(TEXT["rows"], lang)),
        c.Kpi(version_label, tr(TEXT["version"], lang), "transfermarkt-datasets"),
    ]
)
c.status_board(
    status_board(
        q,
        quality=settings.quality,
        analysis=settings.analysis,
        today=pd.Timestamp.today().normalize(),
    ),
    lang,
)

# Coverage
cov = data.coverage.copy()
cov["league"] = cov["competition_id"].map(settings.scope.competitions)
latest = cov[cov["season"] == cov["season"].max()]
smallest = latest.sort_values("players_min_minutes").iloc[0]["league"]
fig = go.Figure()
for i, (season, part) in enumerate(cov.groupby("season")):
    part = part.sort_values("players_min_minutes", ascending=False)
    fig.add_trace(
        go.Bar(
            x=part["league"],
            y=part["players_min_minutes"],
            name=season_label(int(season)),
            marker={"color": CATEGORICAL[i % len(CATEGORICAL)]},
        )
    )
fig.update_layout(
    title=tr(TEXT["coverage_title"], lang).format(
        min=num(settings.analysis.min_minutes, lang), low=smallest
    ),
    barmode="group",
    yaxis={"title": tr(TEXT["players_axis"], lang)},
    height=380,
)
observed = cov[
    [
        "league",
        "season",
        "games",
        "clubs",
        "players",
        "players_min_minutes",
        "first_game",
        "last_game",
    ]
].sort_values(["league", "season"])
c.chart_block(
    fig,
    lang=lang,
    footer=c.source_note(lang, data_cutoff=data.data_cutoff),
    how_to_read=tr(TEXT["coverage_how"], lang),
    observed=observed,
    key="coverage",
)

# Completeness
fields = q.completeness
worst_field, worst_rate = q.completeness_min
labels = [FIELD_LABELS.get(f, {"en": f, "pt": f})[lang] for f in fields]
rates = list(fields.values())
fig = go.Figure(
    go.Bar(
        x=rates,
        y=labels,
        orientation="h",
        marker={
            "color": [
                ATTENTION if r < settings.quality.completeness_min else PRIMARY for r in rates
            ]
        },
        text=[num(r * 100, lang, 1) + "%" for r in rates],
        textposition="outside",
    )
)
fig.add_vline(x=settings.quality.completeness_min, line_dash="dot", line_color=MUTED)
fig.update_layout(
    title=tr(TEXT["complete_title"], lang).format(
        field=FIELD_LABELS.get(worst_field, {"en": worst_field, "pt": worst_field})[lang],
        rate=num(worst_rate * 100, lang, 1) + "%",
    ),
    xaxis={"range": [0, 1.08], "tickformat": ".0%"},
    height=300,
)
c.chart_block(
    fig,
    lang=lang,
    footer=c.source_note(lang, data_cutoff=data.data_cutoff)
    + " · "
    + tr(TEXT["contract_note"], lang).format(share=q.contract_missing_share),
    how_to_read=tr(TEXT["complete_how"], lang),
    key="completeness",
)

# League strength
st.subheader(tr(TEXT["strength"], lang))
st.caption(tr(TEXT["strength_note"], lang))
ls = data.league_strength.sort_values(["season", "strength_index"], ascending=[False, False])
st.dataframe(
    pd.DataFrame(
        {
            tr(TEXT["league"], lang): ls["competition_name"],
            tr(TEXT["season"], lang): ls["season"].map(season_label),
            tr(TEXT["clubs"], lang): ls["clubs"],
            tr(TEXT["squad"], lang): ls["avg_squad_value"],
            tr(TEXT["index"], lang): ls["strength_index"],
            tr(TEXT["eu_games"], lang): ls["european_games"],
            tr(TEXT["eu_ppg"], lang): ls["european_ppg"].astype(float),
        }
    ),
    hide_index=True,
    width="stretch",
    column_config={
        tr(TEXT["squad"], lang): st.column_config.NumberColumn(format="€%,.0f"),
        tr(TEXT["index"], lang): st.column_config.NumberColumn(format="%.0f"),
        tr(TEXT["eu_ppg"], lang): st.column_config.NumberColumn(format="%.2f"),
    },
)

# Limitations and source
st.subheader(tr(TEXT["limits"], lang))
st.markdown("\n".join(f"- {item[lang]}" for item in LIMITATIONS))
c.unavailable_metrics(lang)
st.subheader(tr(TEXT["source"], lang))
manifest = data.manifest
st.markdown(
    "[transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) · CC0 1.0  \n"
    f"SHA-256 `{str(manifest.get('source_sha256', '—'))[:16]}…` · "
    f"{manifest.get('extracted_at', '—')}"
)
