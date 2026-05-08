import os
import json
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END, START
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from tools import get_db, get_schema, executar_sql, strip_codeblock
from prompts import (
    get_question_validation_system,
    get_intent_classification_system,
    get_history_check_system,
    build_sql_system_prompt,
    get_analysis_insight_system,
    get_analysis_summary_system,
    build_analysis_human_prompt,
    get_visualization_system,
    build_visualization_human_prompt,
)

load_dotenv()

# Grafo atual:

    # START validar_pergunta → classificar →  verificar_historico → gerar_sql → validar_sql → executar_sql → analisar → route → [visualizar] → END
    #              |                                   |               ↑             |
    #              └→ END(pergunta fora do escopo)     |               └──   retry   ┘ (se SQL falhar)
    #                                                  |
    #                                                  └→ END (se histórico já responde)

MAX_SQL_RETRIES = 2

# - Estado compartilhado entre os nós do grafo

class AgentState(TypedDict):
    user_message: str
    chat_history: str
    intent: str
    sql_query: str
    sql_result: str
    sql_error: str
    retry_count: int
    analysis: str
    chart_spec: str
    final_response: str


# - Construção do grafo 

def build_graph(db=None):
    if db is None:
        db = get_db()

    # schema_info = get_schema(db)
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    llm = ChatOllama(model=model, temperature=0.0, reasoning=False)

    # - Nó 0: Validar pergunta do usuário

    def validar_pergunta(state: AgentState) -> dict:
        if not state["user_message"].strip():
            return {"final_response": "Por favor, faça uma pergunta válida."}
        
        response = llm.invoke([
            SystemMessage(content=get_question_validation_system()),
            HumanMessage(content=state["user_message"]),
        ])

        try:
            result = json.loads(strip_codeblock(response.content))
            if not result.get("valid", True):
                return {"final_response": f"Pergunta fora do escopo: {result.get('reason', 'não relacionada aos dados disponíveis. Por favor, faça perguntas relacionadas apenas aos dados do negócio.')}"}
        except json.JSONDecodeError:
            pass  # se o LLM não retornar JSON válido, deixa passar

        return {}

    # - Nó 1: Classificar intenção do usuário 

    def classificar(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=get_intent_classification_system()),
            HumanMessage(content=state["user_message"]),
        ])
        intent = response.content.strip().lower()
        if intent not in ("consulta", "visualizacao", "insight"):
            intent = "consulta"
        return {"intent": intent}
    
    # - Nó 1.5: Verificar se o histórico já responde a pergunta

    def verificar_historico(state: AgentState) -> dict:
        history = state.get("chat_history", "").strip()
        intent = state.get("intent", "consulta")

        # Sem histórico ou intent de visualização: sempre vai para SQL
        if not history or intent == "visualizacao":
            return {}

        response = llm.invoke([
            SystemMessage(content=get_history_check_system()),
            HumanMessage(content=
                f"Intent classificado: {intent}\n\n"
                f"Histórico:\n{history}\n\n"
                f"Pergunta atual: {state['user_message']}"
            ),
        ])
        try:
            result = json.loads(strip_codeblock(response.content))
            if result.get("answered"):
                return {"final_response": result.get("response", "")}
        except json.JSONDecodeError:
            pass 
        return {}

    # - Nó 2: Gerar query SQL 

    def gerar_sql(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=build_sql_system_prompt()),
            HumanMessage(content=state["user_message"]),
        ])
        sql = strip_codeblock(response.content)
        return {"sql_query": sql, "retry_count": 0, "sql_error": ""}

    # - Nó 3: Executar SQL no banco 

    def executar(state: AgentState) -> dict:
        result = executar_sql(db, state["sql_query"])

        if isinstance(result, dict) and result.get("error"):
            return {
                "sql_error": result["error"],
                "sql_result": "",
                "retry_count": state.get("retry_count", 0) + 1
            }
        
        return {
            "sql_result": json.dumps(result, ensure_ascii=False, default=str),
            "sql_error": ""
            }
    
    # - Nó 4: Corrigir SQl com base no erro

    def corrigir_sql(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=build_sql_system_prompt()),
            HumanMessage(content=
                            f"A query abaixo retornou um erro. Corrija-a e retorne apenas a query corrigida. \n\n"
                            f"Query anterior: {state['sql_query']} \n\n"
                            f"Erro retornado: {state['sql_error']} \n\n"
                            f"Pergunta original do usuário: {state['user_message']}"
                            f"Histórico da conversa: {state['chat_history', '']}"
                        ),
                    ])
        sql = strip_codeblock(response.content)
        return {"sql_query": sql}

    # - Nó 5: Tratar erro final após tentativas de correção

    def tratar_erro_final(state: AgentState) -> dict:
        return {
            "final_response": (
                "Não foi possível executar a consulta no banco de dados. "
                f"Erro: {state.get('sql_error', 'Erro desconhecido')}. "
                "Por favor, reformule sua pergunta ou tente novamente mais tarde."
            )
        }

    # - Nó 6: Analisar resultados 

    def analisar(state: AgentState) -> dict:
        intent = state.get("intent", "consulta")

        if intent == "insight":
            system = get_analysis_insight_system()
        else:
            system = get_analysis_summary_system()

        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=build_analysis_human_prompt(
                user_message=state["user_message"],
                chat_history=state["chat_history"],
                sql_query=state["sql_query"],
                sql_result=state["sql_result"],
            )),
        ])
        return {"analysis": response.content, "final_response": response.content}

    # ─ Nó 7: Gerar especificação de gráfico Plotly ──────────────────────

    def visualizar(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=get_visualization_system()),
            HumanMessage(content=build_visualization_human_prompt(
                user_message=state["user_message"],
                chat_history=state["chat_history"],
                sql_result=state["sql_result"],
            )),
        ])
        chart = strip_codeblock(response.content)
        analysis = state.get("analysis", "")
        return {
            "chart_spec": chart,
            "final_response": analysis,
        }

    # ─ Roteamento após executar validação de pergunta ───────────────────────

    def route_after_validation(state: AgentState) -> str:
        if state.get("final_response"):
            return "fim"
        return "classificar"
    
    # ─ Roteamento após verificação do histórico ────────────────────────────────────────

    def route_after_history(state: AgentState) -> str:
        if state.get("final_response"):
            return "fim"
        return "gerar_sql"

    # ─ Roteamento após executar SQL ────────────────────────────────────────

    def route_after_sql(state: AgentState) -> str:
        if state.get("sql_error"):
            if state.get("retry_count", 0) < MAX_SQL_RETRIES:
                return "corrigir_sql"
            return "erro_final"
        return "analisar"
    
    # ─ Roteamento condicional após análise ─────────────────────────────────

    def route_after_analysis(state: AgentState) -> str:
        if state.get("intent") == "visualizacao":
            return "visualizar"
        return "fim"

    # ─ Montar o StateGraph ─────────────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("validar_pergunta", validar_pergunta)
    graph.add_node("classificar", classificar)
    graph.add_node("verificar_historico", verificar_historico)
    graph.add_node("gerar_sql", gerar_sql)
    graph.add_node("executar_sql", executar)
    graph.add_node("corrigir_sql", corrigir_sql)
    graph.add_node("erro_final", tratar_erro_final)
    graph.add_node("analisar", analisar)
    graph.add_node("visualizar", visualizar)

    graph.add_edge(START, "validar_pergunta")
    graph.add_conditional_edges("validar_pergunta", route_after_validation, {
    "fim": END,
    "classificar": "classificar",
    })
    graph.add_edge("classificar", "verificar_historico")
    graph.add_conditional_edges("verificar_historico", route_after_history, {
        "fim": END,
        "gerar_sql": "gerar_sql",
    })
    graph.add_edge("gerar_sql", "executar_sql")
    graph.add_conditional_edges("executar_sql", route_after_sql, {
        "corrigir_sql": "corrigir_sql",
        "erro_final": "erro_final",
        "analisar": "analisar",
    })
    graph.add_edge("corrigir_sql", "executar_sql")  # loop de retry
    graph.add_edge("erro_final", END)
    graph.add_conditional_edges("analisar", route_after_analysis, {
        "visualizar": "visualizar",
        "fim": END,
    })
    graph.add_edge("visualizar", END)

    return graph.compile()