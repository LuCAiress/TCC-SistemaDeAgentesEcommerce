import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

st.title("📊 Console SQL (read-only)")
st.markdown("---")

st.markdown(
	"""
	Escreva abaixo uma consulta **SQL** para o banco PostgreSQL.

	- Apenas comandos **SELECT** ou **WITH** são permitidos (read-only)
	- Útil para fazer consultas diretas sobre o dataset Olist
	"""
)

@st.cache_resource
def get_engine():
	url = os.getenv("DATABASE_URL")
	if not url:
		st.error("DATABASE_URL não definida no arquivo .env")
		return None
	return create_engine(url)


engine = get_engine()
if engine is None:
	st.stop()


sql_query = st.text_area(
	"Consulta SQL (apenas SELECT/WITH)",
	height=180,
	placeholder="""-- Exemplo:\nSELECT *\nFROM orders\nLIMIT 10;""",
)

col_run, col_clear = st.columns(2)

with col_run:
	run_query = st.button("▶️ Executar consulta", type="primary", use_container_width=True)
with col_clear:
	clear_state = st.button("🗑️ Limpar", use_container_width=True)


if clear_state:
	st.session_state.pop("last_sql", None)
	st.session_state.pop("last_df", None)
	st.session_state.pop("last_error", None)
	st.rerun()


if run_query:
	query = (sql_query or "").strip()

	if not query:
		st.warning("Digite uma consulta SQL para executar.")
	else:
		normalized = query.lstrip("(").strip().upper()
		if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
			st.error("Apenas consultas **SELECT** ou **WITH** são permitidas.")
		else:
			try:
				with engine.connect() as conn:
					df = pd.read_sql_query(text(query), conn)

				st.session_state["last_sql"] = query
				st.session_state["last_df"] = df
				st.session_state["last_error"] = ""
			except Exception as e:
				st.session_state["last_sql"] = query
				st.session_state["last_df"] = None
				st.session_state["last_error"] = str(e)


last_sql = st.session_state.get("last_sql")
last_df = st.session_state.get("last_df")
last_error = st.session_state.get("last_error")

st.markdown("---")

if last_error:
	st.error(f"Erro ao executar a consulta: {last_error}")
elif last_df is not None:
	st.success(f"Consulta executada com sucesso. {len(last_df)} linha(s) retornada(s).")

	with st.expander("🔍 SQL executada", expanded=False):
		st.code(last_sql or "", language="sql")

	st.dataframe(last_df, use_container_width=True)
else:
	st.info("Nenhuma consulta executada ainda.")

