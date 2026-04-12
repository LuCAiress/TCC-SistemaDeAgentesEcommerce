import streamlit as st
import json
import plotly.graph_objects as go
from tools import get_db
from graph import build_graph

st.title("🐘 Agente de Análise de Dados")

with st.sidebar:
    if st.session_state.get("auth"):
        if st.button("Sair", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ── Conexão com o banco e grafo (cacheados) ──────────────────────────────

@st.cache_resource
def get_agent():
    db = get_db()
    return build_graph(db)

agent = get_agent()

# ── Sidebar ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 💡 Exemplos de perguntas")
    st.markdown(
        "- Quantos pedidos foram feitos por estado?\n"
        "- Me mostre um gráfico das top 10 categorias\n"
        "- Qual a tendência mensal de vendas? Me dê insights\n"
        "- Qual o ticket médio por forma de pagamento?\n"
    )
    st.markdown("---")
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.pg_messages = []
        st.rerun()

# ── Chat ─────────────────────────────────────────────────────────────────

if "pg_messages" not in st.session_state:
    st.session_state.pg_messages = []

for msg in st.session_state.pg_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("chart_spec"):
            try:
                fig = go.Figure(json.loads(msg["chart_spec"]))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
        if msg.get("sql_query"):
            with st.expander("🔍 SQL executada"):
                st.code(msg["sql_query"], language="sql")

if user_query := st.chat_input("Faça uma pergunta sobre o banco de dados"):
    st.session_state.pg_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar="🐘"):
        with st.spinner("Analisando sua pergunta..."):
            result = agent.invoke({
                "user_message": user_query,
                "intent": "",
                "sql_query": "",
                "sql_result": "",
                "analysis": "",
                "chart_spec": "",
                "final_response": "",
            })

        st.markdown(result["final_response"])

        chart_spec = result.get("chart_spec", "")
        if chart_spec:
            try:
                fig = go.Figure(json.loads(chart_spec))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        if result.get("sql_query"):
            with st.expander("🔍 SQL executada"):
                st.code(result["sql_query"], language="sql")

    msg_data = {"role": "assistant", "content": result["final_response"]}
    if chart_spec:
        msg_data["chart_spec"] = chart_spec
    if result.get("sql_query"):
        msg_data["sql_query"] = result["sql_query"]
    st.session_state.pg_messages.append(msg_data)