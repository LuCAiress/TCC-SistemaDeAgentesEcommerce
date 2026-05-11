import os
import json
import ast
import re
import operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from tools import get_db, get_schema, executar_sql, strip_codeblock
from prompts import (
    get_validation_and_classification_system,
    get_history_check_system,
    build_sql_system_prompt,
    get_analysis_insight_system,
    get_analysis_summary_system,
    build_analysis_human_prompt,
    get_visualization_system,
    build_visualization_human_prompt,
)

load_dotenv()

checkpoint_saver = InMemorySaver()

# Converte mensagens do histórico em string para o LLM analisar contexto da conversa
def build_history_from_messages(messages: list, limit: int = 6) -> str:
    lines = []
    for m in messages[-limit:]:
        if isinstance(m, HumanMessage):
            lines.append(f"Usuário: {m.content}")
        elif isinstance(m, AIMessage):
            lines.append(f"Assistente: {m.content}")
    return "\n".join(lines)


def compact_sql_result(
    sql_result: str,
    max_rows: int = 10,
    max_text_length: int = 1200,
    include_sql: bool = False,
) -> str:
    """Reduz o payload enviado ao LLM para análise/visualização."""
    try:
        payload = json.loads(sql_result)
    except Exception:
        payload = None

    if isinstance(payload, dict):
        compact = {}
        if include_sql:
            compact["sql"] = payload.get("sql")
        resultado = payload.get("resultado")

        if isinstance(resultado, str):
            normalized = re.sub(r"Decimal\('([^']+)'\)", r"\1", resultado)
            try:
                parsed = ast.literal_eval(normalized)
            except Exception:
                parsed = resultado
        else:
            parsed = resultado

        if isinstance(parsed, list):
            compact["total_linhas"] = len(parsed)
            compact["linhas_limitadas"] = max_rows
            compact["resultado"] = parsed[:max_rows]
        else:
            compact["resultado"] = parsed

        text = json.dumps(compact, ensure_ascii=False, default=str)
        if len(text) > max_text_length:
            return text[:max_text_length] + "..."
        return text

    if len(sql_result) > max_text_length:
        return sql_result[:max_text_length] + "..."
    return sql_result

MAX_SQL_RETRIES = 2

# Estado compartilhado entre os nós do grafo
class AgentState(TypedDict):
    user_message: str
    messages: Annotated[list[BaseMessage], operator.add]
    intent: str
    sql_query: str
    sql_result: str
    sql_error: str
    retry_count: int
    analysis: str
    chart_spec: str
    final_response: str

# Decorador para injetar o histórico formatado em nós que precisam dessa informação para análise de contexto
def with_history(fn):
    def wrapper(state: AgentState) -> dict:
        history = build_history_from_messages(state.get("messages", []))
        return fn(state, history)
    return wrapper

# Simple in-memory cache to avoid repeated LLM calls for same (message+history)
validation_cache: dict = {}

# Construção do grafo 
def build_graph(db=None):
    if db is None:
        db = get_db()

    # schema_info = get_schema(db)
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    llm = ChatOllama(model=model, temperature=0.0, reasoning=False)
    llm_fast = ChatOllama(model=model, temperature=0.3, reasoning=False)  # LLM mais rápido para análise
    
    # ------------------------------------------------------------------
    # Nodes - (Estados)
    # ------------------------------------------------------------------

    # Nó unificado: validar + classificar + verificar histórico (uma chamada LLM ou heurísticas/cache)
    @with_history
    def validar_classificar_e_verificar(state: AgentState, history: str) -> dict:
        if not state["user_message"].strip():
            return {"final_response": "Por favor, faça uma pergunta válida."}

        text_lower = state["user_message"].lower()
        # Heurística local para visualização (evita LLM quando claro)
        viz_keywords = ("gráfico", "grafico", "plot", "visualização", "visualizacao", "chart")
        if any(k in text_lower for k in viz_keywords):
            return {"intent": "visualizacao"}

        # Cache key = (mensagem, histórico)
        cache_key = (state["user_message"], history)
        cached = validation_cache.get(cache_key)
        if cached:
            return cached.copy()

        # Chamada única ao LLM pedindo validação, intent e se histórico já responde
        combined_system = (
            get_validation_and_classification_system()
            + "\n\n"
            + get_history_check_system()
            + "\n\nRetorne APENAS um JSON com as chaves: "
            + "valid (bool), intent (consulta|visualizacao|insight), answered (bool), response (string)."
        )

        response = llm.invoke([
            SystemMessage(content=combined_system),
            HumanMessage(content=f"Histórico:\n{history}\n\nPergunta atual: {state['user_message']}")
        ])

        try:
            result = json.loads(strip_codeblock(response.content))
        except Exception:
            result = {"valid": True, "intent": "consulta", "answered": False, "response": ""}

        if not result.get("valid", True):
            msg = (
                "Não foi possível processar sua pergunta: talvez não esteja relacionada aos dados disponíveis. "
                "Por favor, faça perguntas relacionadas apenas aos dados do negócio."
            )
            out = {"final_response": msg, "messages": [HumanMessage(content=state["user_message"]), AIMessage(content=msg)]}
            validation_cache[cache_key] = out
            return out

        if result.get("answered"):
            resposta = result.get("response", "")
            out = {"final_response": resposta, "messages": [HumanMessage(content=state["user_message"]), AIMessage(content=resposta)]}
            validation_cache[cache_key] = out
            return out

        intent = result.get("intent", "consulta")
        if intent not in ("consulta", "visualizacao", "insight"):
            intent = "consulta"
        out = {"intent": intent}
        validation_cache[cache_key] = out
        return out

    # Nó 2: Gerar SQL a partir da pergunta do usuário
    def gerar_sql(state: AgentState) -> dict:
        response = llm.invoke([
            SystemMessage(content=build_sql_system_prompt()),
            HumanMessage(content=state["user_message"]),
        ])
        sql = strip_codeblock(response.content)
        return {"sql_query": sql, "retry_count": 0, "sql_error": ""}

    # Nó 3: Executar SQL no banco PostgreSQL
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
                        ),
                    ])
        sql = strip_codeblock(response.content)
        return {"sql_query": sql}

    # - Nó 5: Tratar erro final após tentativas de correção
    def tratar_erro_final(state: AgentState) -> dict:
        resposta = (
                "Não foi possível executar a consulta no banco de dados. "
                f"Erro: {state.get('sql_error', 'Erro desconhecido')}. "
                "Por favor, reformule sua pergunta ou tente novamente mais tarde."
            )
        return {
            "final_response": resposta,
            "messages": [HumanMessage(content=state["user_message"]), AIMessage(content=resposta)]
        }

    # - Nó 6: Analisar resultados 
    def analisar(state: AgentState) -> dict:
        intent = state.get("intent", "consulta")

        if intent == "visualizacao":
            return {"analysis": None, "final_response": None}  # pula de análise para visualização
        
        if intent == "insight":
            system = get_analysis_insight_system()
        else:
            system = get_analysis_summary_system()

        # Compactar resultado antes de enviar
        compact_result = compact_sql_result(
            state["sql_result"],
            max_rows=10,
            max_text_length=900,
            include_sql=False,
        )

        response = llm_fast.invoke([
            SystemMessage(content=system),
            HumanMessage(content=build_analysis_human_prompt(
                user_message=state["user_message"],
                sql_result=compact_result,
            )),
        ])
        return {
            "analysis": response.content,
            "final_response": response.content,
            "messages": [HumanMessage(content=state["user_message"]), AIMessage(content=response.content)]
        }

    # ─ Nó 7: Gerar especificação de gráfico Plotly ──────────────────────
    def visualizar(state: AgentState) -> dict:
        # Compactar resultado antes de enviar
        compact_result = compact_sql_result(
            state["sql_result"],
            max_rows=14,
            max_text_length=1200,
            include_sql=False,
        )
        
        response = llm_fast.invoke([
            SystemMessage(content=get_visualization_system()),
            HumanMessage(content=build_visualization_human_prompt(
                user_message=state["user_message"],
                sql_result=compact_result,
            )),
        ])
        chart = strip_codeblock(response.content)
        
        # Mensagem para contexto no histórico: descrição do gráfico gerado
        dados = state.get("sql_result", "")
        history_msg = (
            f"[Gráfico gerado para: '{state['user_message']}']\n"
            f"Dados: {dados}"
        )
        return {
            "chart_spec": chart,
            "final_response": "",
            "messages": [HumanMessage(content=state["user_message"]), AIMessage(content=history_msg)]
        }
        
    # ------------------------------------------------------------------
    # EDGES - (Roteadores)
    # ------------------------------------------------------------------

    # Roteamento após nó unificado de validação/classificação/cheque de histórico
    def route_after_validation(state: AgentState) -> str:
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

    # ------------------------------------------------------------------
    # GRAPH - Montagem da lógica do agente com o grafo de estados
    # ------------------------------------------------------------------

    graph = StateGraph(AgentState)

    graph.add_node("validar_classificar_e_verificar", validar_classificar_e_verificar)
    graph.add_node("gerar_sql", gerar_sql)
    graph.add_node("executar_sql", executar)
    graph.add_node("corrigir_sql", corrigir_sql)
    graph.add_node("erro_final", tratar_erro_final)
    graph.add_node("analisar", analisar)
    graph.add_node("visualizar", visualizar)

    graph.add_edge(START, "validar_classificar_e_verificar")
    graph.add_conditional_edges("validar_classificar_e_verificar", route_after_validation, {
        "fim": END,
        "gerar_sql": "gerar_sql",
    })
    graph.add_edge("gerar_sql", "executar_sql")
    graph.add_conditional_edges("executar_sql", route_after_sql, {
        "corrigir_sql": "corrigir_sql",
        "erro_final": "erro_final",
        "analisar": "analisar",
    })
    graph.add_edge("corrigir_sql", "executar_sql")
    graph.add_edge("erro_final", END)
    graph.add_conditional_edges("analisar", route_after_analysis, {
        "visualizar": "visualizar",
        "fim": END,
    })
    graph.add_edge("visualizar", END)

    return graph.compile(checkpointer=checkpoint_saver)