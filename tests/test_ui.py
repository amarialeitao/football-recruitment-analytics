"""UI tests: pure helpers directly, Streamlit rendering through AppTest. Data is invented."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from streamlit.testing.v1 import AppTest

from scouting.app_data import DataNotReadyError, build_app_data
from scouting.config import DEFAULT_CONFIG_PATH, load_settings
from scouting.health import StatusItem
from scouting.ingest import transfermarkt as tm
from scouting.insights import Insight
from scouting.ui import components, i18n, theme
from scouting.ui.filters import Filters, apply_filters

# --- i18n --------------------------------------------------------------------------------------


def test_every_text_has_both_languages() -> None:
    for key, texts in i18n.TEXTS.items():
        assert set(texts) == {"en", "pt"}, key
        assert all(texts.values()), key


def test_missing_text_raises() -> None:
    with pytest.raises(KeyError, match="nope"):
        i18n.t("nope", "en")


# --- filters -----------------------------------------------------------------------------------


def test_apply_filters(ps: pd.DataFrame) -> None:
    f = Filters(
        season=2025,
        competitions=("AA1",),
        positions=("Defender",),
        age_range=(20, 30),
        min_minutes=900,
        max_market_value=5e6,
    )
    out = apply_filters(ps, f)
    assert len(out) > 0
    assert set(out["competition_id"]) == {"AA1"}
    assert set(out["position_group"]) == {"Defender"}
    assert out["age"].between(20, 30).all()
    assert (out["minutes"] >= 900).all()
    assert (out["market_value_end"] <= 5e6).all()


def test_apply_filters_keeps_unknown_age(ps: pd.DataFrame) -> None:
    ps.loc[0, "age"] = None
    f = Filters(season=2025, competitions=tuple(ps["competition_id"].unique()))
    assert 0 in apply_filters(ps, f).index


# --- theme and components (pure HTML) ----------------------------------------------------------


def test_plotly_template_uses_theme_colours() -> None:
    template = theme.plotly_template()
    assert list(template.layout.colorway) == theme.CATEGORICAL


def test_kpi_html_escapes_text() -> None:
    out = components.kpi_html([components.Kpi("<b>1</b>", "Players", "note & more")])
    assert "&lt;b&gt;1&lt;/b&gt;" in out and "note &amp; more" in out


def test_insight_html_has_marker_text_and_badge() -> None:
    insight = Insight("k", {"en": "Top 5%.", "pt": "Top 5%."}, "medium", kind="observation")
    out = components.insight_html(insight, "pt")
    assert components.OBSERVATION_MARKER in out
    assert "confiança média" in out


def test_status_board_html_shows_label_not_only_colour() -> None:
    item = StatusItem({"en": "Area", "pt": "Área"}, "attention", {"en": "Why", "pt": "Porquê"})
    out = components.status_board_html([item], "pt")
    assert "Atenção" in out and "Área" in out and "Porquê" in out


def test_source_note_by_language() -> None:
    cutoff = pd.Timestamp("2026-05-24")
    en = components.source_note("en", data_cutoff=cutoff, season_label="2025/26", population="n=10")
    pt = components.source_note("pt", data_cutoff=cutoff, season_label="2025/26")
    assert en == (
        "Source: transfermarkt-datasets (CC0) · Season 2025/26 · Data to 2026-05-24 · n=10"
    )
    assert pt.startswith("Fonte:") and "Dados até 2026-05-24" in pt


# --- app data ----------------------------------------------------------------------------------


def _settings_for(tmp_path: Path):
    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["scope"]["seasons"] = [2025]
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_settings(path)


def test_build_app_data_requires_local_data(tmp_path: Path) -> None:
    with pytest.raises(DataNotReadyError, match="fetch_data.py"):
        build_app_data(_settings_for(tmp_path), today=pd.Timestamp("2026-10-22"))


def test_build_app_data_from_extract(source_db: Path, tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    tm.extract(source_db, settings.processed_dir / "transfermarkt", ["PO1"], [2025])
    data = build_app_data(settings, today=pd.Timestamp("2026-10-22"))
    assert set(data.players["player_id"]) == {10, 11}
    assert "goals_p90_pct" in data.players.columns
    assert "value_ratio" in data.players.columns
    assert data.players["competition_name"].iloc[0] == "Liga Portugal"
    assert data.seasons == [2025]
    assert set(data.valuations["player_id"]) <= {10, 11}
    assert data.valuations["date"].is_monotonic_increasing
    assert data.quality.games == 1
    assert data.data_cutoff == pd.Timestamp("2025-09-01")


# --- Streamlit rendering -----------------------------------------------------------------------


def _component_gallery() -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    from metric_data import synthetic_player_season
    from scouting.config import load_settings
    from scouting.health import StatusItem
    from scouting.insights import Insight
    from scouting.ui import components as c
    from scouting.ui.filters import language_selector, sidebar_filters

    lang = language_selector()
    settings = load_settings()
    df = synthetic_player_season()
    df["competition_id"] = df["competition_id"].map({"AA1": "PO1", "BB1": "ES1"})
    _, universe, selection = sidebar_filters(df, settings)
    c.page_header("Gallery", "Which components render?")
    c.kpi_row([c.Kpi(str(len(selection)), "Players"), c.Kpi("€2.0m", "Median value")])
    insight = Insight("k", {"en": "A fact.", "pt": "Um facto."}, "high", kind="observation")
    c.chart_block(
        go.Figure(go.Bar(x=[1, 2], y=[3, 4])),
        lang=lang,
        footer=c.source_note(lang, data_cutoff=pd.Timestamp("2026-05-24")),
        how_to_read="Bars.",
        insights=[insight],
        observed=selection.head(3)[["player_id", "minutes"]],
    )
    item = StatusItem({"en": "Area", "pt": "Área"}, "ok", {"en": "Fine", "pt": "Bem"})
    c.status_board([item], lang)
    c.unavailable_metrics(lang)
    st.write(f"universe={len(universe)}")


def test_components_render_without_errors() -> None:
    at = AppTest.from_function(_component_gallery, default_timeout=30)
    at.run()
    assert not at.exception
    assert at.title[0].value == "Gallery"
    assert any("universe=" in m.value for m in at.markdown)


def test_language_toggle_switches_texts() -> None:
    at = AppTest.from_function(_component_gallery, default_timeout=30)
    at.run()
    assert at.sidebar.button[0].label == "Clear filters"
    at.session_state["lang_selector"] = "pt"
    at.run()
    assert not at.exception
    assert at.sidebar.button[0].label == "Limpar filtros"


# --- shared charts -----------------------------------------------------------------------------


def test_percentile_profile_bars_and_comparison(ps: pd.DataFrame) -> None:
    from scouting.metrics.percentiles import percentile_ranks
    from scouting.ui import charts

    ranked = percentile_ranks(ps, min_minutes=0)
    keys = ["goals_p90", "assists_p90"]
    one = charts.percentile_profile(ranked.iloc[0], keys, "en", title="T")
    assert len(one.data) == 1 and len(one.data[0].x) == 2
    assert max(one.data[0].x) <= 100
    two = charts.percentile_profile(
        ranked.iloc[0], keys, "pt", title="T", compare=ranked.iloc[1], names=("A", "B")
    )
    assert len(two.data) == 2
    assert two.layout.xaxis.title.text.startswith("Percentil vs")
    assert "100 = melhor" in two.layout.xaxis.title.text


def test_value_trajectory_and_minutes_charts() -> None:
    from scouting.ui import charts

    vals = pd.DataFrame(
        {"date": pd.to_datetime(["2024-01-01", "2025-01-01"]), "market_value_in_eur": [1e6, 2e6]}
    )
    fig = charts.value_trajectory(vals, "en", title="V", season=2025)
    assert list(fig.data[0].y) == [1e6, 2e6]
    rows = pd.DataFrame(
        {
            "season": [2024, 2025],
            "competition_id": ["AA1", "AA1"],
            "competition_name": ["League A", "League A"],
            "minutes": [500, 1500],
            "minutes_share": [0.2, 0.6],
        }
    )
    bars = charts.minutes_by_season(rows, "en", title="M")
    assert list(bars.data[0].text) == ["20%", "60%"]


def test_sequential_shades_end_on_black() -> None:
    from scouting.ui.theme import INK, sequential_shades

    assert sequential_shades(3)[-1] == INK
    assert len(sequential_shades(3)) == 3
    assert sequential_shades(6) == [INK] * 6


def test_column_help_exists_in_both_languages() -> None:
    from scouting.ui.columns import HELP, help_text

    for key, texts in HELP.items():
        assert set(texts) == {"en", "pt"}, key
    assert "1,800" in help_text("confidence", "en", medium=900, high=1800)


def test_as_percent_does_not_change_the_source() -> None:
    from scouting.ui.columns import as_percent

    df = pd.DataFrame({"share": [0.5, 0.9395]})
    out = as_percent(df, ["share"])
    assert out["share"].tolist() == [50.0, 93.95]
    assert df["share"].tolist() == [0.5, 0.9395]
