from langchain_core.tools import tool
from langchain_community.utilities import SQLDatabase


def get_db():
    return SQLDatabase.from_uri(
        "postgresql+psycopg2://postgres:1234@localhost:5432/Ecommerce-TCC"
    )


def create_consultar_postgres(db: SQLDatabase):
    @tool
    def consultar_postgres(query: str):
        """
        Executa uma consulta SQL no banco PostgreSQL.
        Use esta tool SEMPRE que precisar de dados do banco.
        """
        try:
            result = db.run(query)
            return {"sql": query, "resultado": result}
        except Exception as e:
            return {"erro": str(e)}

    return consultar_postgres
