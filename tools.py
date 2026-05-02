import os
import json
from decimal import Decimal
from datetime import datetime, date
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

load_dotenv()

def get_db() -> SQLDatabase:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida no .env")
    return SQLDatabase.from_uri(url)

def get_schema(db: SQLDatabase) -> str:
    return db.table_info

def strip_codeblock(text: str) -> str:
    """Remove delimitadores de bloco Markdown se presentes."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end]).strip()
    return text

def executar_sql(db: SQLDatabase, query: str) -> dict:
    """Executa SQL read-only no banco PostgreSQL."""
    normalized = query.strip().lstrip("(").upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return {"error": "Apenas consultas SELECT/WITH são permitidas."}
    try:
        result = db.run(query)
        return {"sql": query, "resultado": result}
    except Exception as e:
        return {"error": str(e)}
