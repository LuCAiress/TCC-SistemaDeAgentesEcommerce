import os
import json
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END, START
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from tools import get_db, get_schema, executar_sql, strip_codeblock

load_dotenv()


# ── Estado compartilhado entre os nós do grafo ───────────────────────────

class AgentState(TypedDict):
    user_message: str
    intent: str
    sql_query: str
    sql_result: str
    analysis: str
    chart_spec: str
    final_response: str


# ── Construção do grafo ──────────────────────────────────────────────────

def build_graph(db=None):
    if db is None:
        db = get_db()

    schema_info = get_schema(db)
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    llm = ChatOllama(model=model, temperature=0.0, reasoning=False)

    # ── Nó 1: Classificar intenção do usuário ────────────────────────────

    def classificar(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=(
                "Classifique a intenção do usuário em EXATAMENTE uma categoria:\n"
                "- cltaonsu: quer dados, números, listas, contagens\n"
                "- visualizacao: quer gráfico, chart, comparação visual, mapa\n"
                "- insight: quer análise de negócio, tendência, explicação, recomendação\n\n"
                "Responda APENAS com a palavra da categoria, sem explicação."
            )),
            HumanMessage(content=state["user_message"]),
        ])
        intent = response.content.strip().lower()
        if intent not in ("consulta", "visualizacao", "insight"):
            intent = "consulta"
        return {"intent": intent}

    # ── Nó 2: Gerar query SQL ────────────────────────────────────────────

    def gerar_sql(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=(
                "Você é um especialista em SQL PostgreSQL.\n"
                "Gere APENAS a query SQL (sem explicação) para responder à pergunta.\n"
                "Use apenas SELECT (read-only). Nunca use DELETE, UPDATE, INSERT, DROP.\n\n"
                f"Schema do banco:\n{schema_info}"
            )),
            HumanMessage(content=state["user_message"]),
        ])
        sql = strip_codeblock(response.content)
        return {"sql_query": sql}

    # ── Nó 3: Executar SQL no banco ──────────────────────────────────────

    def executar(state: AgentState) -> dict:
        result = executar_sql(db, state["sql_query"])
        return {"sql_result": json.dumps(result, ensure_ascii=False, default=str)}

    # ── Nó 4: Analisar resultados ────────────────────────────────────────

    def analisar(state: AgentState) -> dict:
        intent = state.get("intent", "consulta")

        if intent == "insight":
            system = (
                "Você é um analista de negócios sênior de e-commerce. "
                "Com base nos dados reais do banco, forneça:\n"
                "1. **Interpretação** dos números\n"
                "2. **Tendências ou padrões** identificados\n"
                "3. **Possíveis causas** para os resultados\n"
                "4. **Recomendações** de ação para o negócio\n\n"
                "Seja específico e baseie-se nos dados. Não invente informações."
            )
        else:
            system = (
                "Resuma os resultados da consulta SQL de forma clara e objetiva. "
                "Formate dados tabulares como tabela Markdown quando apropriado."
            )

        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=(
                f"Pergunta do usuário: {state['user_message']}\n\n"
                f"SQL executada:\n```sql\n{state['sql_query']}\n```\n\n"
                f"Resultado:\n{state['sql_result']}"
            )),
        ])
        return {"analysis": response.content, "final_response": response.content}

    # ── Nó 5: Gerar especificação de gráfico Plotly ──────────────────────

    def visualizar(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=(
                "Gere um JSON válido de especificação Plotly para visualizar os dados.\n"
                'O JSON deve ser: {"data": [...], "layout": {...}}\n'
                "Use tipos adequados: bar, line, pie, scatter, etc.\n"
                "Responda APENAS com o JSON, sem texto ao redor."
            )),
            HumanMessage(content=(
                f"Pergunta: {state['user_message']}\n\n"
                f"Dados:\n{state['sql_result']}"
            )),
        ])
        chart = strip_codeblock(response.content)
        analysis = state.get("analysis", "")
        return {
            "chart_spec": chart,
            "final_response": analysis,
        }

    # ── Roteamento condicional após análise ──────────────────────────────

    def route_after_analysis(state: AgentState) -> str:
        if state.get("intent") == "visualizacao":
            return "visualizar"
        return "fim"

    # ── Montar o StateGraph ──────────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("classificar", classificar)
    graph.add_node("gerar_sql", gerar_sql)
    graph.add_node("executar_sql", executar)
    graph.add_node("analisar", analisar)
    graph.add_node("visualizar", visualizar)

    graph.add_edge(START, "classificar")
    graph.add_edge("classificar", "gerar_sql")
    graph.add_edge("gerar_sql", "executar_sql")
    graph.add_edge("executar_sql", "analisar")
    graph.add_conditional_edges("analisar", route_after_analysis, {
        "visualizar": "visualizar",
        "fim": END,
    })
    graph.add_edge("visualizar", END)

    return graph.compile()
