"""Player Finder: filter the market and export a shortlist."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scouting.metrics.catalog import metric
from scouting.ui import columns as col
from scouting.ui import components as c
from scouting.ui import shortlist as sl
from scouting.ui.data import setup_page
from scouting.ui.filters import language_selector, sidebar_filters
from scouting.ui.i18n import num, position_label
from scouting.ui.players import (
    confidence_for_minutes,
    go_to,
    money,
    next_contract_deadline,
    season_label,
    tr,
)

TEXT = {
    "title": {"en": "Player Finder", "pt": "Pesquisa de jogadores"},
    "question": {
        "en": "Who fits the profile we need, within our budget?",
        "pt": "Quem encaixa no perfil que procuramos, dentro do orçamento?",
    },
    "contract": {"en": "Contract ends by", "pt": "Contrato termina até"},
    "any": {"en": "Any", "pt": "Qualquer"},
    "sort": {"en": "Sort by", "pt": "Ordenar por"},
    "players": {"en": "players match your filters", "pt": "jogadores cumprem os filtros"},
    "players_note": {
        "en": "season {season}, listed below",
        "pt": "época {season}, na lista abaixo",
    },
    "median_age": {"en": "typical age in this list", "pt": "idade típica nesta lista"},
    "median_value": {"en": "typical market value in this list", "pt": "valor típico nesta lista"},
    "median_note": {
        "en": "median: half are above, half below",
        "pt": "mediana: metade acima, metade abaixo",
    },
    "expiring": {
        "en": "have a contract ending by {date}",
        "pt": "têm contrato a terminar até {date}",
    },
    "expiring_note": {
        "en": "a contract close to its end usually lowers the fee",
        "pt": "um contrato perto do fim costuma baixar o valor da transferência",
    },
    "export": {"en": "Download shortlist (CSV)", "pt": "Descarregar lista (CSV)"},
    "open": {"en": "Open profile", "pt": "Abrir perfil"},
    "pick": {
        "en": "Select a row to open the player's profile.",
        "pt": "Selecione uma linha para abrir o perfil do jogador.",
    },
    "contract_note": {
        "en": "Contract dates are a snapshot at the data cut-off and may have changed since.",
        "pt": "As datas de contrato são do momento do corte dos dados e podem ter mudado.",
    },
    # Table columns
    "name": {"en": "Player", "pt": "Jogador"},
    "club": {"en": "Club", "pt": "Clube"},
    "league": {"en": "League", "pt": "Liga"},
    "position": {"en": "Position", "pt": "Posição"},
    "age": {"en": "Age", "pt": "Idade"},
    "minutes": {"en": "Minutes", "pt": "Minutos"},
    "value": {"en": "Market value", "pt": "Valor de mercado"},
    "contract_end": {"en": "Contract end", "pt": "Fim de contrato"},
    "value_ratio": {"en": "Value vs expected", "pt": "Valor vs esperado"},
    "confidence": {"en": "Confidence", "pt": "Confiança"},
}

SORT_OPTIONS = ["goal_contributions_p90", "plus_minus_on_p90", "minutes_share", "minutes"]


def build_table(df: pd.DataFrame, lang: str, thresholds: tuple[int, int]) -> pd.DataFrame:
    """The shortlist as shown and exported (pure, no Streamlit)."""
    out = pd.DataFrame(
        {
            tr(TEXT["name"], lang): df["name"],
            tr(TEXT["club"], lang): df["club_name"],
            tr(TEXT["league"], lang): df["competition_name"],
            tr(TEXT["position"], lang): df["sub_position"].map(lambda p: position_label(p, lang)),
            tr(TEXT["age"], lang): df["age"],
            tr(TEXT["minutes"], lang): df["minutes"],
            metric("goal_contributions_p90").label_for(lang): df["goal_contributions_p90"].astype(
                float
            ),
            metric("plus_minus_on_p90").label_for(lang): df["plus_minus_on_p90"].astype(float),
            metric("minutes_share").label_for(lang): df["minutes_share"],
            tr(TEXT["value"], lang): df["market_value_end"],
            tr(TEXT["value_ratio"], lang): df["value_ratio"],
            tr(TEXT["contract_end"], lang): df["contract_expiration_date"].dt.date,
            tr(TEXT["confidence"], lang): [
                c.t(f"confidence_{confidence_for_minutes(m, thresholds)}", lang)
                for m in df["minutes"]
            ],
        }
    )
    return out.reset_index(drop=True)


settings, data = setup_page("Player Finder")
lang = language_selector()
filters, universe, selection = sidebar_filters(data.players, settings)
c.page_header(tr(TEXT["title"], lang), tr(TEXT["question"], lang))

season = filters.season
next_summer = next_contract_deadline(data.data_cutoff)
contract_options = [None, next_summer, next_summer + pd.DateOffset(years=1)]
col1, col2 = st.columns(2)
contract_by = col1.selectbox(
    tr(TEXT["contract"], lang),
    contract_options,
    format_func=lambda d: tr(TEXT["any"], lang) if d is None else d.date().isoformat(),
)
sort_key = col2.selectbox(
    tr(TEXT["sort"], lang), SORT_OPTIONS, format_func=lambda k: metric(k).label_for(lang)
)

shortlist = selection
if contract_by is not None:
    shortlist = shortlist[shortlist["contract_expiration_date"] <= contract_by]
shortlist = shortlist.sort_values(sort_key, ascending=False)

if shortlist.empty:
    st.info(c.t("no_data", lang))
    st.stop()

expiring = (shortlist["contract_expiration_date"] <= next_summer).mean()
c.kpi_row(
    [
        c.Kpi(
            num(len(shortlist), lang),
            tr(TEXT["players"], lang),
            tr(TEXT["players_note"], lang).format(season=season_label(season)),
        ),
        c.Kpi(
            num(shortlist["age"].median(), lang, 1),
            tr(TEXT["median_age"], lang),
            tr(TEXT["median_note"], lang),
        ),
        c.Kpi(
            money(shortlist["market_value_end"].median(), lang),
            tr(TEXT["median_value"], lang),
            tr(TEXT["median_note"], lang),
        ),
        c.Kpi(
            f"{expiring:.0%}",
            tr(TEXT["expiring"], lang).format(date=next_summer.date().isoformat()),
            tr(TEXT["expiring_note"], lang),
        ),
    ]
)

thresholds = (
    settings.analysis.confidence_minutes.medium,
    settings.analysis.confidence_minutes.high,
)
table = build_table(shortlist, lang, thresholds)
st.caption(tr(TEXT["pick"], lang))
share_name = metric("minutes_share").label_for(lang)
event = st.dataframe(
    col.as_percent(table, [share_name]),
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        tr(TEXT["name"], lang): st.column_config.TextColumn(pinned=True),
        tr(TEXT["age"], lang): st.column_config.NumberColumn(format="%.1f"),
        tr(TEXT["minutes"], lang): st.column_config.NumberColumn(format="%d"),
        metric("goal_contributions_p90").label_for(lang): col.number(
            "goal_contributions_p90", lang, "%.2f"
        ),
        metric("plus_minus_on_p90").label_for(lang): col.number("plus_minus_on_p90", lang, "%+.2f"),
        share_name: col.share("minutes_share", lang),
        tr(TEXT["value"], lang): col.money("market_value", lang, tr(TEXT["value"], lang)),
        tr(TEXT["value_ratio"], lang): col.number("value_ratio", lang, "%.2fx"),
        tr(TEXT["confidence"], lang): col.text(
            "confidence", lang, medium=thresholds[0], high=thresholds[1]
        ),
    },
)

rows = event.selection.rows if event and event.selection else []
left, middle, right = st.columns([1, 1, 1])
if rows:
    chosen = shortlist.iloc[rows[0]]
    if left.button(f"{tr(TEXT['open'], lang)}: {chosen['name']}", type="primary"):
        go_to("profile", chosen)
    sl.toggle_button(chosen, lang, key="finder_shortlist", container=middle)
right.download_button(
    tr(TEXT["export"], lang),
    data=table.to_csv(index=False).encode("utf-8"),
    file_name=f"shortlist_{season_label(season).replace('/', '-')}.csv",
    mime="text/csv",
)
st.caption(
    c.source_note(
        lang,
        data_cutoff=data.data_cutoff,
        season_label=season_label(season),
        population=tr(TEXT["contract_note"], lang),
    )
)
