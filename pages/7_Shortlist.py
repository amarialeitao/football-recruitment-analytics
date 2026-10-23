"""Shortlist: the players a scout collected from other pages, compared side by side."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scouting.insights import POSITION_LABEL, format_money
from scouting.metrics.catalog import PROFILE_METRICS, metric
from scouting.metrics.percentiles import PCT_SUFFIX
from scouting.ui import charts
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui import shortlist as sl
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector
from scouting.ui.i18n import num, position_label
from scouting.ui.players import go_to, player_key, season_label, tr

TEXT = {
    "title": {"en": "Shortlist", "pt": "Lista de observação"},
    "question": {
        "en": "Who are we following, and how do they compare?",
        "pt": "Quem estamos a acompanhar, e como se comparam?",
    },
    "empty": {
        "en": "The shortlist is empty. Add players with the **Add to shortlist** button on "
        "Player Profile, or after selecting a row in Player Finder, Similar Players, Value Finder "
        "or Potential.",
        "pt": "A lista está vazia. Adicione jogadores com o botão **Adicionar à lista** no Perfil "
        "do jogador, ou depois de selecionar uma linha na Pesquisa, Jogadores parecidos, Valor de "
        "mercado ou Potencial.",
    },
    "kept": {
        "en": "The list is kept while the app is open. Download it to keep or share it.",
        "pt": "A lista mantém-se enquanto a aplicação estiver aberta. Descarregue-a para a "
        "guardar ou partilhar.",
    },
    "pick": {
        "en": "Select up to {n} players to compare them side by side.",
        "pt": "Selecione até {n} jogadores para os comparar lado a lado.",
    },
    "too_many": {
        "en": "Comparing the first {n} selected players.",
        "pt": "A comparar os primeiros {n} jogadores selecionados.",
    },
    "mixed": {
        "en": "Percentiles compare each player with his own position group, so the chart needs "
        "players from the same group. The table below still compares everyone selected.",
        "pt": "Os percentis comparam cada jogador com o seu grupo de posição, por isso o gráfico "
        "precisa de jogadores do mesmo grupo. A tabela abaixo compara todos os selecionados.",
    },
    "chart_title": {
        "en": "{names}: percentile profiles side by side",
        "pt": "{names}: perfis de percentis lado a lado",
    },
    "chart_how": {
        "en": "Each bar is a player's percentile among {group} with at least {min} minutes in "
        "the same season, across all leagues in scope (100 = best; for cards and goals conceded, "
        "fewer is better). Players from different leagues or seasons are each compared with their "
        "own season's peers. The dotted line marks the median.",
        "pt": "Cada barra é o percentil do jogador entre {group} com pelo menos {min} minutos na "
        "mesma época, em todas as ligas analisadas (100 = melhor; em cartões e golos sofridos, "
        "menos é melhor). Jogadores de ligas ou épocas diferentes são comparados com os pares da "
        "sua época. A linha pontilhada marca a mediana.",
    },
    "low_minutes": {
        "en": "Fewer than {min} minutes: {names}. Percentiles are not shown for them.",
        "pt": "Menos de {min} minutos: {names}. Os percentis não são mostrados.",
    },
    "facts": {"en": "Side by side", "pt": "Lado a lado"},
    "remove": {"en": "Remove selected", "pt": "Retirar selecionados"},
    "clear": {"en": "Clear shortlist", "pt": "Limpar lista"},
    "export": {"en": "Download shortlist (CSV)", "pt": "Descarregar lista (CSV)"},
    "open": {"en": "Open profile", "pt": "Abrir perfil"},
    # Table and fact rows
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "league": {"en": "League", "pt": "Liga"},
    "season": {"en": "Season", "pt": "Época"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "share": {"en": "Share of team minutes", "pt": "% dos minutos da equipa"},
    "score": {"en": "Performance score", "pt": "Índice de rendimento"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "ratio": {"en": "Value vs expected", "pt": "Valor vs esperado"},
    "contract": {"en": "Contract until", "pt": "Contrato até"},
    "pct": {"en": "percentile", "pt": "percentil"},
}

settings, data = setup_page("Shortlist")
lang = language_selector()
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))
min_minutes = settings.analysis.min_minutes

listed = sl.rows(data.players).reset_index(drop=True)
if listed.empty:
    st.info(tr(TEXT["empty"], lang))
    st.stop()

# --- the list --------------------------------------------------------------------------------
table = pd.DataFrame(
    {
        tr(TEXT["name"], lang): listed["name"],
        tr(TEXT["club"], lang): listed["club_name"],
        tr(TEXT["league"], lang): listed["competition_name"],
        tr(TEXT["season"], lang): listed["season"].map(lambda s: season_label(int(s))),
        tr(TEXT["position"], lang): listed["sub_position"].map(lambda p: position_label(p, lang)),
        tr(TEXT["age"], lang): listed["age"],
        tr(TEXT["minutes"], lang): listed["minutes"],
        tr(TEXT["share"], lang): listed["minutes_share"],
        tr(TEXT["score"], lang): listed["performance_score"],
        tr(TEXT["value"], lang): listed["market_value_end"],
        tr(TEXT["ratio"], lang): listed["value_ratio"],
        tr(TEXT["contract"], lang): listed["contract_expiration_date"].dt.date,
    }
)
st.caption(tr(TEXT["pick"], lang).format(n=sl.MAX_COMPARE))
event = st.dataframe(
    col.as_percent(table, [tr(TEXT["share"], lang)]),
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="multi-row",
    key="shortlist_table",
    column_config={
        tr(TEXT["name"], lang): st.column_config.TextColumn(pinned=True),
        tr(TEXT["age"], lang): st.column_config.NumberColumn(format="%.1f"),
        tr(TEXT["share"], lang): col.share("minutes_share", lang),
        tr(TEXT["score"], lang): col.number("performance_score", lang, "%.0f"),
        tr(TEXT["value"], lang): col.money("market_value", lang, tr(TEXT["value"], lang)),
        tr(TEXT["ratio"], lang): col.number("value_ratio", lang, "%.2fx"),
    },
)
selected = list(event.selection.rows) if event and event.selection else []

actions = iter(st.columns(4))
if selected and next(actions).button(tr(TEXT["remove"], lang), icon=":material/bookmark_remove:"):
    for i in selected:
        sl.remove(player_key(listed.iloc[i]))
    st.rerun()
if next(actions).button(tr(TEXT["clear"], lang), icon=":material/delete_sweep:"):
    sl.clear()
    st.rerun()
next(actions).download_button(
    tr(TEXT["export"], lang),
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="shortlist.csv",
    mime="text/csv",
    icon=":material/download:",
)
st.caption(tr(TEXT["kept"], lang))

# --- comparison ------------------------------------------------------------------------------
if not selected:
    # Default: the first players added from the same position group as the first one.
    first_group = listed.iloc[0]["position_group"]
    selected = list(listed.index[listed["position_group"] == first_group][: sl.MAX_COMPARE])
elif len(selected) > sl.MAX_COMPARE:
    st.caption(tr(TEXT["too_many"], lang).format(n=sl.MAX_COMPARE))
    selected = selected[: sl.MAX_COMPARE]
chosen = [listed.iloc[i] for i in selected]

groups = {p["position_group"] for p in chosen}
regulars = [p for p in chosen if p["minutes"] >= min_minutes]
too_few = [p for p in chosen if p["minutes"] < min_minutes]
if len(groups) > 1:
    st.info(tr(TEXT["mixed"], lang))
elif regulars and next(iter(groups)) in PROFILE_METRICS:
    group = next(iter(groups))
    names = [str(p["name"]) for p in regulars]
    c.chart_block(
        charts.percentile_compare(
            regulars,
            names,
            list(PROFILE_METRICS[group]),
            lang,
            title=tr(TEXT["chart_title"], lang).format(names=" · ".join(names)),
        ),
        lang=lang,
        footer=c.source_note(lang, data_cutoff=data.data_cutoff),
        how_to_read=tr(TEXT["chart_how"], lang).format(
            group=POSITION_LABEL[lang][group], min=num(min_minutes, lang)
        ),
        key="shortlist_compare",
    )
if too_few:
    st.caption(
        tr(TEXT["low_minutes"], lang).format(
            min=num(min_minutes, lang), names=", ".join(str(p["name"]) for p in too_few)
        )
    )


def _metric_cell(player: pd.Series, key: str) -> str:
    value, pct = player.get(key), player.get(key + PCT_SUFFIX)
    if value is None or pd.isna(value):
        return "—"
    text = metric(key).fmt.format(float(value))
    if lang == "pt":
        text = text.replace(".", ",")
    return text if pct is None or pd.isna(pct) else f"{text} ({tr(TEXT['pct'], lang)} {pct:.0f})"


def _cell(value, kind: str) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return "—"
    if kind == "money":
        return format_money(float(value), lang)
    if kind == "share":
        return f"{float(value):.0%}"
    if kind == "ratio":
        return f"{num(float(value), lang, 2)}x"
    if kind == "int":
        return num(float(value), lang)
    if kind == "dec":
        return num(float(value), lang, 1)
    if kind == "date":
        return pd.Timestamp(value).date().isoformat()
    return str(value)


fact_rows = [
    ("club", "club_name", "text"),
    ("league", "competition_name", "text"),
    ("season", "season_label", "text"),
    ("age", "age", "dec"),
    ("minutes", "minutes", "int"),
    ("score", "performance_score", "int"),
    ("value", "market_value_end", "money"),
    ("ratio", "value_ratio", "ratio"),
    ("contract", "contract_expiration_date", "date"),
]
facts = {
    tr(TEXT["name"], lang): [tr(TEXT[label], lang) for label, _, _ in fact_rows],
}
metric_keys = [] if len(groups) > 1 else list(PROFILE_METRICS.get(next(iter(groups)), ()))
if "minutes_share" not in metric_keys:  # always show it; with its percentile when available
    fact_rows.insert(5, ("share", "minutes_share", "share"))
facts[tr(TEXT["name"], lang)] += [metric(k).label_for(lang) for k in metric_keys]
for player in chosen:
    values = [_cell(player.get(column), kind) for _, column, kind in fact_rows]
    values += [_metric_cell(player, k) for k in metric_keys]
    facts[str(player["name"])] = values
st.subheader(tr(TEXT["facts"], lang))
facts_frame = pd.DataFrame(facts)
# Tall enough to show every row without an inner scroll bar (35 px per row plus the header).
st.dataframe(facts_frame, hide_index=True, width="stretch", height=35 * (len(facts_frame) + 1) + 3)

open_cols = st.columns(max(1, len(chosen)))
for i, (player, column) in enumerate(zip(chosen, open_cols, strict=False)):
    if column.button(f"{tr(TEXT['open'], lang)}: {player['name']}", key=f"open_{i}"):
        go_to("profile", player)
st.caption(c.source_note(lang, data_cutoff=data.data_cutoff))
