"""Entry point: page navigation. Run with ``streamlit run app.py``."""

import streamlit as st

from scouting.ui.players import PAGES

TITLES = {
    "finder": {"en": "Player Finder", "pt": "Pesquisa de jogadores"},
    "profile": {"en": "Player Profile", "pt": "Perfil do jogador"},
}

lang = st.session_state.get("lang", "en")
pages = [
    st.Page(PAGES[key], title=title[lang], default=(i == 0))
    for i, (key, title) in enumerate(TITLES.items())
]
st.navigation(pages).run()
