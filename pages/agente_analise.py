import streamlit as st
import json
import plotly.graph_objects as go
from tools import get_db
from graph import build_graph
from utils import logout

# ── Config da página ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente de Análise de Dados",
    page_icon="🐘",
    layout="wide",
)

st.title("🐘 Agente de Análise de Dados")

# ── Conexão com o banco e grafo (cacheados) ──────────────────────────────
@st.cache_resource
def get_agent():
    db = get_db()
    return build_graph(db)

agent = get_agent()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    logout()
    st.markdown("### 💡 Exemplos de perguntas")
    examples = [
        "Quantos pedidos foram feitos por estado?",
        "Me mostre um gráfico das top 10 categorias",
        "Qual a tendência mensal de vendas? Me dê insights",
        "Qual o ticket médio por forma de pagamento?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"ex_{ex}"):
            st.session_state["prefill_input"] = ex

    st.markdown("---")
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.pg_messages = []
        st.session_state.pop("prefill_input", None)
        st.rerun()

# ── Inicialização do estado ───────────────────────────────────────────────
if "pg_messages" not in st.session_state:
    st.session_state.pg_messages = []

# ── Histórico de contexto para o LLM (sem chart_spec, só texto) ──────────
def build_chat_history(messages: list, limit: int = 6) -> str:
    """
    Usa apenas as últimas `limit` trocas.
    Exclui chart_spec do contexto — não ajuda o LLM e desperdiça tokens.
    """
    relevant = [m for m in messages if m["role"] in ("user", "assistant")][-limit:]
    lines = []
    for msg in relevant:
        role = "Usuário" if msg["role"] == "user" else "Assistente"
        # Inclui só o texto, não o sql nem o chart
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)

# ── Renderiza uma mensagem individual ────────────────────────────────────
def render_message(msg: dict):
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🐘"):
        st.markdown(msg["content"])

        if msg.get("chart_spec"):
            try:
                fig = go.Figure(json.loads(msg["chart_spec"]))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Não foi possível renderizar o gráfico: {e}")

        if msg.get("sql_query"):
            with st.expander("🔍 SQL executada"):
                st.code(msg["sql_query"], language="sql")

        if msg.get("sql_result"):
            with st.expander("📄 Resultado bruto (JSON)"):
                try:
                    parsed = json.loads(msg["sql_result"])
                    st.json(parsed)
                except Exception:
                    st.text(msg["sql_result"])

# ── Renderiza histórico ───────────────────────────────────────────────────
for msg in st.session_state.pg_messages:
    render_message(msg)

# ── Input do usuário ─────────────────────────────────────────────────────
# Suporte a clique nos exemplos da sidebar
prefill = st.session_state.pop("prefill_input", None)
user_query = st.chat_input("Faça uma pergunta sobre o banco de dados") or prefill

if user_query:
    # Registra e exibe a mensagem do usuário
    st.session_state.pg_messages.append({"role": "user", "content": user_query})
    render_message(st.session_state.pg_messages[-1])

    with st.chat_message("assistant", avatar="🐘"):
        status = st.status("Analisando sua pergunta...", expanded=False)

        # Monta contexto com histórico (sem a pergunta atual que já está em pg_messages)
        history = build_chat_history(st.session_state.pg_messages[:-1])
        full_prompt = (
            f"Histórico da conversa:\n{history}\n\nPergunta atual:\n{user_query}"
            if history
            else user_query  # sem histórico, manda só a pergunta — menos ruído
        )

        try:
            result = agent.invoke({
                "user_message": full_prompt,
                "intent": "",
                "sql_query": "",
                "sql_result": "",
                "analysis": "",
                "chart_spec": "",
                "final_response": "",
            })
            status.update(label="✅ Concluído", state="complete")
        except Exception as e:
            status.update(label="❌ Erro", state="error")
            st.error(f"Erro ao processar sua pergunta: {e}")
            st.stop()

        final_response = result.get("final_response", "")
        chart_spec = result.get("chart_spec", "")
        sql_query = result.get("sql_query", "")
        sql_result = result.get("sql_result", "")

        # Exibe resposta principal
        st.markdown(final_response)

        # Exibe gráfico se existir
        if chart_spec:
            try:
                fig = go.Figure(json.loads(chart_spec))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Não foi possível renderizar o gráfico: {e}")

        # SQL e resultado bruto em expanders
        if sql_query:
            with st.expander("🔍 SQL executada"):
                st.code(sql_query, language="sql")

        if sql_result:
            with st.expander("📄 Resultado bruto (JSON)"):
                try:
                    st.json(json.loads(sql_result))
                except Exception:
                    st.text(sql_result)

    # Salva mensagem do assistente no histórico
    st.session_state.pg_messages.append({
        "role": "assistant",
        "content": final_response,
        "chart_spec": chart_spec,
        "sql_query": sql_query,
        "sql_result": sql_result,
    })

# import streamlit as st
# import json
# import plotly.graph_objects as go
# from tools import get_db
# from graph import build_graph
# from utils import logout

# st.title("🐘 Agente de Análise de Dados")

# with st.sidebar:
#     logout()
            
# # ── Função para construir histórico ──────────────────────────────────────

# def build_chat_history(messages, limit=5):
#     history = ""
#     for msg in messages[-limit:]:
#         role = "Usuário" if msg["role"] == "user" else "Assistente"
#         history += f"{role}: {msg['content']}\n"
#     return history

# # ── Conexão com o banco e grafo (cacheados) ──────────────────────────────

# @st.cache_resource
# def get_agent():
#     db = get_db()
#     return build_graph(db)

# agent = get_agent()

# # ── Sidebar ──────────────────────────────────────────────────────────────

# with st.sidebar:
#     st.markdown("### 💡 Exemplos de perguntas")
#     st.markdown(
#         "- Quantos pedidos foram feitos por estado?\n"
#         "- Me mostre um gráfico das top 10 categorias\n"
#         "- Qual a tendência mensal de vendas? Me dê insights\n"
#         "- Qual o ticket médio por forma de pagamento?\n"
#     )
#     st.markdown("---")
#     if st.button("🗑️ Limpar conversa", use_container_width=True):
#         st.session_state.pg_messages = []
#         st.rerun()

# # ── Chat ─────────────────────────────────────────────────────────────────

# if "pg_messages" not in st.session_state:
#     st.session_state.pg_messages = []

# for msg in st.session_state.pg_messages:
#     with st.chat_message(msg["role"]):
#         st.markdown(msg["content"])
#         if msg.get("chart_spec"):
#             try:
#                 fig = go.Figure(json.loads(msg["chart_spec"]))
#                 st.plotly_chart(fig, use_container_width=True)
#             except Exception:
#                 pass
#         if msg.get("sql_query"):
#             with st.expander("🔍 SQL executada"):
#                 st.code(msg["sql_query"], language="sql")

# if user_query := st.chat_input("Faça uma pergunta sobre o banco de dados"):
#     st.session_state.pg_messages.append({"role": "user", "content": user_query})

#     with st.chat_message("user", avatar="🧑‍💻"):
#         st.markdown(user_query)

#     with st.chat_message("assistant", avatar="🐘"):
#         with st.spinner("Analisando sua pergunta..."):

#             history = build_chat_history(st.session_state.pg_messages)

#             full_prompt = f"""
# Histórico da conversa:
# {history}

# Pergunta atual:
# {user_query}
# """

#             result = agent.invoke({
#                 "user_message": full_prompt,
#                 "intent": "",
#                 "sql_query": "",
#                 "sql_result": "",
#                 "analysis": "",
#                 "chart_spec": "",
#                 "final_response": "",
#             })

#         st.markdown(result["final_response"])