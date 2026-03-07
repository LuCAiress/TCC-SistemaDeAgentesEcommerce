import streamlit as st

# ── Definição das páginas ────────────────────────────────────────────────

home = st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True)
postgres = st.Page("pages/2_Postgres.py", title="Agente Postgres", icon="🐘")

pg = st.navigation([home, postgres])

st.set_page_config(
    page_title="TCC - Agentes com LLM",
    page_icon="🤖",
    layout="centered",
)

pg.run()
            