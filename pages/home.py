import streamlit as st
from utils import logout

with st.sidebar:
    logout()

st.title("TCC — Sistema de Agentes para Análise de Negócios")
st.markdown("---")

st.markdown(
    """
    Este projeto demonstra o uso de **agentes inteligentes** com grafos de
    raciocínio (**LangGraph**) integrados a um LLM local via **Ollama**, para
    análise de dados de e-commerce em linguagem natural.
    """
)

st.subheader("🏗️ Arquitetura do Sistema")

st.markdown(
    """
    O sistema utiliza um **StateGraph** (LangGraph) com 5 nós especializados:

    """
)

col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    st.image(
        "images\Intenção Classificação to-2026-03-22-194622.png",
        caption="Arquitetura do grafo de intenção e geração de insights",
        width=300,
    )


st.subheader("🛠️ Tecnologias Utilizadas")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        **LLM & Agentes**
        - LangGraph (StateGraph)
        - LangChain
        - Ollama (LLM local)
        """
    )

with col2:
    st.markdown(
        """
        **Dados**
        - PostgreSQL
        - Dataset Olist (8 tabelas)
        - +100k pedidos reais
        """
    )

with col3:
    st.markdown(
        """
        **Interface**
        - Streamlit
        - Plotly (gráficos)
        - Chat interativo
        """
    )

st.markdown("---")
st.subheader("📌 Páginas")
st.markdown(
    """
    Use o menu lateral para navegar:

    - **🐘 Agente de Análise de Dados** — Faça perguntas em linguagem natural
      sobre o banco de dados. O sistema classifica sua intenção, gera SQL,
      executa e analisa os resultados automaticamente.
    """
)
