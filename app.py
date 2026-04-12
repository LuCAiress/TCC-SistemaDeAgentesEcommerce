import streamlit as st

st.set_page_config(
    page_title="TCC - Agentes de Análise de Negócios",
    page_icon="🤖",
    layout="wide",
)

st.logo("images/logoCEUB.png", size="large")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] * {
        font-size: 1.05rem !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        font-size: 1.05rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "auth" not in st.session_state:
    st.session_state["auth"] = False

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
postgres = st.Page("pages/agente_analise.py", title="Agente de Análise", icon="🐘")
sql_console = st.Page("pages/pagina_consulta.py", title="Console SQL", icon="📊")
dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📈")
login_page = st.Page("pages/login.py", title="Login", icon="🔐", default=not st.session_state["auth"])

if st.session_state["auth"]:
    pages = [home, postgres, sql_console, dashboard]
else:
    pages = [login_page]

pg = st.navigation(pages)

pg.run()