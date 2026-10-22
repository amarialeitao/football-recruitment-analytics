"""The single cached data loader used by every page.

``st.cache_data`` lives only here, so the data is read and enriched once per session and
filter changes never reload it.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from scouting.app_data import AppData, DataNotReadyError, build_app_data
from scouting.config import ConfigError, Settings, load_settings
from scouting.ui.i18n import t
from scouting.ui.theme import CSS, register_plotly_template


@st.cache_resource(show_spinner=False)
def get_settings(config_path: str | None = None) -> Settings:
    return load_settings(config_path)


@st.cache_data(show_spinner="Loading data…")
def _load(config_path: str | None, today: str) -> AppData:
    return build_app_data(get_settings(config_path), today=pd.Timestamp(today))


def setup_page(title: str) -> tuple[Settings, AppData]:
    """Page config, theme and data. Stops the page with a readable error if data is missing."""
    st.set_page_config(page_title=title, page_icon="⚽", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    register_plotly_template()

    config_path = os.environ.get("SCOUTING_CONFIG")
    lang = st.session_state.get("lang", "en")
    try:
        settings = get_settings(config_path)
        data = _load(config_path, pd.Timestamp.today().normalize().isoformat())
    except (ConfigError, DataNotReadyError, FileNotFoundError) as error:
        st.error(f"**{t('data_not_ready', lang)}**\n\n{error}")
        st.stop()
    return settings, data
