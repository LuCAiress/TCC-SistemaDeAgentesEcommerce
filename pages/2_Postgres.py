import streamlit as st
from langchain_core.messages import HumanMessage
from tools import get_db
from graph import build_agent

st.title("🐘 Agente Postgres")

# ── Conexão com o banco e agente (cacheados) ─────────────────────────────

@st.cache_resource
def get_agent():
    db = get_db()
    return build_agent(db)

agent = get_agent()

# ── Sidebar ──────────────────────────────────────────────────────────────

with st.sidebar:
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.pg_messages = []
        st.rerun()

# ── Chat ─────────────────────────────────────────────────────────────────

if "pg_messages" not in st.session_state:
    st.session_state.pg_messages = []

for msg in st.session_state.pg_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_query := st.chat_input("Faça uma pergunta sobre o banco de dados"):
    st.session_state.pg_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar="🐘"):
        with st.spinner("Consultando o banco..."):
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_query)]}
            )
            full_response = result["messages"][-1].content

        st.markdown(full_response)

    st.session_state.pg_messages.append({"role": "assistant", "content": full_response})
