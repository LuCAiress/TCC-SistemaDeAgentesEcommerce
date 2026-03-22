import streamlit as st

st.title("🤖 TCC — Sistema de Agentes para Análise de Negócios")
st.markdown("---")

st.markdown(
    """
    Este projeto demonstra o uso de **agentes inteligentes** com grafos de
    raciocínio (**LangGraph**) integrados a um LLM local via **Ollama**, para
    análise de dados de e-commerce em linguagem natural.
    """
)

# ── Arquitetura do sistema ───────────────────────────────────────────────

st.subheader("🏗️ Arquitetura do Sistema")

st.markdown(
    """
    O sistema utiliza um **StateGraph** (LangGraph) com 5 nós especializados:

    ```
    ┌─────────────────┐
    │   Classificar    │  ← Identifica a intenção do usuário
    │   Intenção       │    (consulta / visualização / insight)
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │   Gerar SQL      │  ← LLM gera a query PostgreSQL
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  Executar SQL    │  ← Executa no banco (read-only)
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │    Analisar      │  ← LLM interpreta os dados
    │   Resultados     │    (análise simples ou insight de negócio)
    └────────┬────────┘
             │
        ┌────┴────┐
        ▼         ▼
    [  FIM  ]  ┌──────────┐
               │ Gerar     │  ← Se o usuário pediu gráfico
               │ Gráfico   │    (Plotly chart)
               └─────┬────┘
                     ▼
                 [  FIM  ]
    ```
    """
)

# ── Tecnologias ──────────────────────────────────────────────────────────

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

# ── Navegação ────────────────────────────────────────────────────────────

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
