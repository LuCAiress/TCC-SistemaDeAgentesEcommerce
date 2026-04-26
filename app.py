import streamlit as st
from utils import get_cookie_controller

st.set_page_config(
    page_title="TCC - Agentes de Análise de Negócios",
    page_icon="🤖",
    layout="wide",
)


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

controller = get_cookie_controller()

if "auth" not in st.session_state:
    token = controller.get("auth_user")
    role = controller.get("auth_role")
    if token:
        st.session_state["auth"] = True
        st.session_state["user_name"] = token
        st.session_state["user_role"] = role
    else:
        st.session_state["auth"] = False

if "theme" not in st.session_state:
    st.session_state["theme"] = st.context.theme.type

# Verificar se o tema mudou a cada segundo para atualizar o logo dinamicamente
@st.fragment(run_every=1)
def _watch_theme():
    current = st.context.theme.type
    if current != st.session_state["theme"]:
        st.session_state["theme"] = current
        st.rerun(scope="app")

_watch_theme()

if st.session_state["theme"] == "dark":
    st.logo("images\logoCEUBDark.png", size="large")
else:
    st.logo("images\logoCEUBLight.png", size="large")

home = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
postgres = st.Page("pages/agente_analise.py", title="Agente de Análise", icon="🐘")
sql_console = st.Page("pages/pagina_consulta.py", title="Console SQL", icon="📊")
dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📈")
login_page = st.Page("pages/login.py", title="Login", icon="🔐", default=not st.session_state["auth"])
registration_page = st.Page("pages/admin.py", title="Admin", icon="🛠️")

if st.session_state["auth"]:
    if st.session_state.get("user_role") == "admin":
        pages = [home, postgres, sql_console, dashboard, registration_page]
    else:
        pages = [home, postgres, sql_console, dashboard]
else:
    pages = [login_page]

pg = st.navigation(pages)

pg.run()