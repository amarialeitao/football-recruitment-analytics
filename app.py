"""Entry point: page navigation. Run with ``streamlit run app.py``."""

import os

import streamlit as st

from scouting.config import ConfigError
from scouting.glossary import entries
from scouting.ui.data import get_settings
from scouting.ui.flow import routed
from scouting.ui.players import PAGES

TITLES = {
    "overview": {"en": "Market Overview", "pt": "Visão geral"},
    "finder": {"en": "Player Finder", "pt": "Pesquisa de jogadores"},
    "profile": {"en": "Player Profile", "pt": "Perfil do jogador"},
    "similar": {"en": "Similar Players", "pt": "Jogadores parecidos"},
    "value": {"en": "Value Finder", "pt": "Valor de mercado"},
    "potential": {"en": "Potential", "pt": "Potencial"},
    "quality": {"en": "Data Quality", "pt": "Qualidade dos dados"},
    "shortlist": {"en": "Shortlist", "pt": "Lista de observação"},
}

# The colours follow Casa Pia's identity, so say clearly whose app this is.
GLOSSARY_TITLE = {
    "en": "Glossary: what the terms mean",
    "pt": "Glossário: o que os termos querem dizer",
}

DISCLAIMER = {
    "en": "Independent portfolio project, not affiliated with or endorsed by Casa Pia AC. "
    "Data: transfermarkt-datasets (CC0).",
    "pt": "Projeto de portefólio independente, sem ligação nem aprovação do Casa Pia AC. "
    "Dados: transfermarkt-datasets (CC0).",
}

lang = st.session_state.get("lang", "en")
# The shortlist page shows how many players it holds, so it is visible from every page.
n_shortlisted = len(st.session_state.get("shortlist", []))
pages = [
    st.Page(
        PAGES[key],
        title=f"{title[lang]} ({n_shortlisted})" if key == "shortlist" else title[lang],
        default=(i == 0),
    )
    for i, (key, title) in enumerate(TITLES.items())
]


def sidebar_footer() -> None:
    """Glossary and disclaimer at the bottom of the sidebar, in the page's language."""
    lang = st.session_state.get("lang", "en")
    with st.sidebar.expander(GLOSSARY_TITLE[lang], icon=":material/menu_book:"):
        try:
            settings = get_settings(os.environ.get("SCOUTING_CONFIG"))
        except ConfigError:
            return  # the page already shows the configuration error
        st.markdown("\n\n".join(f"**{term}**: {text}" for term, text in entries(settings, lang)))
    st.sidebar.markdown(
        f'<div class="sc-disclaimer">{DISCLAIMER[lang]}</div>', unsafe_allow_html=True
    )


# The footer goes after the page so it sits at the bottom of the sidebar. Pages that end early
# call end_page() (see scouting.ui.flow) instead of st.stop(), so the footer still appears.
with routed():  # pages that end early (end_page) still get the footer below
    st.navigation(pages).run()
sidebar_footer()
