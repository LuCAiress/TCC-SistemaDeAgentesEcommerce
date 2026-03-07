from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_community.utilities import SQLDatabase

from tools import get_db, create_consultar_postgres


def build_agent(db: SQLDatabase | None = None):
    if db is None:
        db = get_db()

    consultar_postgres = create_consultar_postgres(db)
    schema_info = db.table_info

    system_prompt = f"""
    Você é um agente que consulta um banco PostgreSQL.

    REGRAS OBRIGATÓRIAS:
    - Você DEVE chamar uma tool para responder.
    - É PROIBIDO responder sem chamar uma tool.
    - Nunca invente dados.
    - Nunca simule resultados.
    - Se não for possível responder com SQL válido, chame a tool mesmo assim e retorne erro.

    A ÚNICA tool disponível é:
    - consultar_postgres(sql: string)

    Você deve:
    1) Gerar uma consulta SQL
    2) Chamar a tool consultar_postgres com essa SQL
    3) Aguardar o resultado
    4) Somente então responder

    Formate suas respostas seguindo este modelo:
    SQL: a consulta SQL gerada formatado como código Markdown
    Resultado: o resultado real retornado pela ferramenta, formatado como tabela
    Interpretação: uma breve interpretação do resultado, se necessário

    Schema do banco:
    {schema_info}
    """

    return create_agent(
        tools=[consultar_postgres],
        model=ChatOllama(model="qwen3:8b", temperature=0.0, reasoning=False),
        system_prompt=system_prompt,
    )
