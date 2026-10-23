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

# The colours follow Casa Pia's identity, so say clearly whose app this is.
DISCLAIMER = {
    "en": "Independent portfolio project, not affiliated with or endorsed by Casa Pia AC. "
    "Data: transfermarkt-datasets (CC0).",
    "pt": "Projeto de portefólio independente, sem ligação nem aprovação do Casa Pia AC. "
    "Dados: transfermarkt-datasets (CC0).",
}

lang = st.session_state.get("lang", "en")
pages = [
    st.Page(PAGES[key], title=title[lang], default=(i == 0))
    for i, (key, title) in enumerate(TITLES.items())
]
st.navigation(pages).run()

# After the page, so it sits at the bottom of the sidebar (the page may have changed language).
st.sidebar.markdown(
    f'<div class="sc-disclaimer">{DISCLAIMER[st.session_state.get("lang", "en")]}</div>',
    unsafe_allow_html=True,
)
