
import os

from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase

load_dotenv()

def get_db() -> SQLDatabase:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida no .env")
    return SQLDatabase.from_uri(url)

def get_schema(db: SQLDatabase) -> str:
    return db.table_info

print (get_schema(get_db()))