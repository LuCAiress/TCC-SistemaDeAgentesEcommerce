import streamlit as st

# ── Definição das páginas ────────────────────────────────────────────────

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
postgres = st.Page("pages/agente_analise.py", title="Agente de Análise", icon="🐘")

pg = st.navigation([home, postgres])

st.set_page_config(
    page_title="TCC - Agentes de Análise de Negócios",
    page_icon="🤖",
    layout="centered",
)

pg.run()
            