"""Entry point: page navigation. Run with ``streamlit run app.py``."""

import streamlit as st

from scouting.ui.players import PAGES

TITLES = {
    "overview": {"en": "Market Overview", "pt": "Visão geral"},
    "finder": {"en": "Player Finder", "pt": "Pesquisa de jogadores"},
    "profile": {"en": "Player Profile", "pt": "Perfil do jogador"},
    "similar": {"en": "Similar Players", "pt": "Jogadores parecidos"},
    "value": {"en": "Value Finder", "pt": "Valor de mercado"},
    "potential": {"en": "Potential", "pt": "Potencial"},
    "quality": {"en": "Data Quality", "pt": "Qualidade dos dados"},
}

lang = st.session_state.get("lang", "en")
pages = [
    st.Page(PAGES[key], title=title[lang], default=(i == 0))
    for i, (key, title) in enumerate(TITLES.items())
]
st.navigation(pages).run()
