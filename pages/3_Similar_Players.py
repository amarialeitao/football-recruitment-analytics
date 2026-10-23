"""Similar Players: who plays a similar statistical role to a reference player."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.metrics.similarity import find_similar
from scouting.ui import charts
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label, t
from scouting.ui.players import go_to, money, player_label, player_selector, season_label, tr

TEXT = {
    "title": {"en": "Similar Players", "pt": "Jogadores parecidos"},
    "question": {
        "en": "Who could replace this player, within our filters?",
        "pt": "Quem poderia substituir este jogador, dentro dos nossos filtros?",
    },
    "reference": {"en": "Reference player", "pt": "Jogador de referência"},
    "top_n": {"en": "Number of candidates", "pt": "Número de candidatos"},
    "past": {"en": "Include previous seasons", "pt": "Incluir épocas anteriores"},
    "weights": {"en": "Adjust metric weights", "pt": "Ajustar pesos das métricas"},
    "weights_note": {
        "en": "0 ignores a metric; 3 makes it count three times as much.",
        "pt": "0 ignora a métrica; 3 faz com que conte o triplo.",
    },
    "below_min": {
        "en": "The reference player has fewer than {min} minutes: his profile is a first "
        "impression, and so is the list below.",
        "pt": "O jogador de referência tem menos de {min} minutos: o perfil é uma primeira "
        "impressão, e a lista abaixo também.",
    },
    "none": {
        "en": "No candidate matches the filters. Widen the leagues, age or value in the sidebar.",
        "pt": "Nenhum candidato corresponde aos filtros. Alargue ligas, idade ou valor na barra "
        "lateral.",
    },
    "pick": {
        "en": "Select a row to compare the candidate with the reference.",
        "pt": "Selecione uma linha para comparar o candidato com a referência.",
    },
    "compare_title": {
        "en": "{cand} vs {ref}: percentile profiles side by side",
        "pt": "{cand} vs {ref}: perfis em percentis lado a lado",
    },
    "how": {
        "en": "Similarity compares the position group's profile metrics after putting each on the "
        "same scale (z-score) within all players of that group with at least {min} minutes. "
        "100 means an identical profile. It finds players with a similar statistical role "
        "in the available data (usage, goal output, results on the pitch), not players of "
        "the same quality: passing, defending and shot quality are not in public data.",
        "pt": "A similaridade compara as métricas do perfil da posição depois de as pôr na mesma "
        "escala (z-score) entre todos os jogadores do grupo com pelo menos {min} minutos. 100 "
        "significa perfil idêntico. Encontra jogadores com um papel estatístico parecido nos "
        "dados disponíveis (uso, produção de golos, resultados em campo), não jogadores da "
        "mesma qualidade: passe, defesa e qualidade de remate não existem em dados públicos.",
    },
    "open": {"en": "Open profile", "pt": "Abrir perfil"},
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "league": {"en": "League", "pt": "Liga"},
    "season": {"en": "Season", "pt": "Época"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "similarity": {"en": "Similarity", "pt": "Similaridade"},
}

settings, data = setup_page("Similar Players")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))

reference = player_selector(
    universe,
    lang,
    label=tr(TEXT["reference"], lang),
    prefer_competition=settings.scope.focus_competition,
)
if reference is None:
    st.stop()

min_minutes = settings.analysis.min_minutes
if reference["minutes"] < min_minutes:
    st.warning(tr(TEXT["below_min"], lang).format(min=num(min_minutes, lang)))

group = reference["position_group"]
keys = list(PROFILE_METRICS[group])
col1, col2 = st.columns([2, 1])
top_n = col1.slider(tr(TEXT["top_n"], lang), 5, 25, 10)
include_past = col2.toggle(tr(TEXT["past"], lang), value=False)
with st.expander(tr(TEXT["weights"], lang)):
    st.caption(tr(TEXT["weights_note"], lang))
    cols = st.columns(min(4, len(keys)))
    weights = {
        key: cols[i % len(cols)].slider(
            metric(key).label_for(lang), 0.0, 3.0, 1.0, 0.5, key=f"w_{group}_{key}"
        )
        for i, key in enumerate(keys)
    }

seasons = data.seasons if include_past else [filters.season]
results = find_similar(
    data.players,
    {
        "player_id": reference["player_id"],
        "season": reference["season"],
        "competition_id": reference["competition_id"],
    },
    min_minutes=min_minutes,
    weights=weights,
    seasons=seasons,
    competitions=filters.competitions,
    max_age=filters.age_range[1],
    max_market_value=filters.max_market_value,
    top_n=top_n * 3,  # room for the minimum-age filter below
)
results = results[results["age"].isna() | (results["age"] >= filters.age_range[0])].head(top_n)

if results.empty:
    st.info(tr(TEXT["none"], lang))
    st.stop()

table = pd.DataFrame(
    {
        tr(TEXT["name"], lang): results["name"],
        tr(TEXT["club"], lang): results["club_name"],
        tr(TEXT["league"], lang): results["competition_name"],
        tr(TEXT["season"], lang): results["season"].map(season_label),
        tr(TEXT["position"], lang): results["sub_position"].map(lambda p: position_label(p, lang)),
        tr(TEXT["age"], lang): results["age"],
        tr(TEXT["minutes"], lang): results["minutes"],
        tr(TEXT["value"], lang): results["market_value_end"],
        tr(TEXT["similarity"], lang): results["similarity"],
    }
)
st.caption(tr(TEXT["pick"], lang))
event = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        tr(TEXT["name"], lang): st.column_config.TextColumn(pinned=True),
        tr(TEXT["age"], lang): st.column_config.NumberColumn(format="%.1f"),
        tr(TEXT["value"], lang): col.money("market_value", lang, tr(TEXT["value"], lang)),
        tr(TEXT["similarity"], lang): st.column_config.ProgressColumn(
            format="%.0f", min_value=0, max_value=100, help=col.help_text("similarity", lang)
        ),
    },
)
rows = event.selection.rows if event and event.selection else []
candidate = results.iloc[rows[0] if rows else 0]

ref_name, cand_name = str(reference["name"]), str(candidate["name"])
c.chart_block(
    charts.percentile_profile(
        candidate,
        keys,
        lang,
        title=tr(TEXT["compare_title"], lang).format(cand=cand_name, ref=ref_name),
        compare=reference,
        names=(cand_name, ref_name),
    ),
    lang=lang,
    footer=c.source_note(
        lang,
        data_cutoff=data.data_cutoff,
        season_label=season_label(int(candidate["season"])),
        population=f"{t(group, lang)} · {num(min_minutes, lang)}+ min",
    ),
    how_to_read=tr(TEXT["how"], lang).format(min=num(min_minutes, lang)),
    key="compare",
)
st.caption(f"{player_label(candidate)} · {money(candidate['market_value_end'], lang)}")
if st.button(f"{tr(TEXT['open'], lang)}: {cand_name}", type="primary"):
    go_to("profile", candidate)
