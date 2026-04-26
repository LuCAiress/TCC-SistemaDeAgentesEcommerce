import os

import streamlit as st
import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from utils import get_cookie_controller, get_auth_table_config

load_dotenv()

st.markdown(
	"""<h1 style='text-align: center;'>🔐 Login</h1>""",
	unsafe_allow_html=True,
)

# Deixar o formulário de login mais estreito e centralizado
st.markdown(
	"""
	<style>
	div[data-testid="stForm"] {
		max-width: 480px;
		margin: 0 auto;
	}
	</style>
	""",
	unsafe_allow_html=True,
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
 
schema, table, user_field, password_field, role_field = get_auth_table_config()

def autenticar_usuario(username: str, password: str):

	query = text(
		f"SELECT user_id, {user_field} AS username, {password_field} AS senha, {role_field} AS role "
		f"FROM {schema}.{table} WHERE {user_field} = :username LIMIT 1"
	)

	with engine.connect() as conn:
		row = conn.execute(query, {"username": username}).mappings().first()

	if not row:
		return False, "Usuário ou senha inválida."

	dados = dict(row)
	hashed_from_db = dados["senha"].encode("utf-8")

	if not bcrypt.checkpw(password.encode("utf-8"), hashed_from_db):
		return False, "Senha inválida."

	st.session_state["user_name"] = dados.get("username") or username
	st.session_state["user_role"] = dados.get("role")
	return True, ""


if st.session_state.get("auth"):
	st.success(f"Você já está autenticado como {st.session_state.get('user_name', '')}.")
	if st.button("Ir para a Home"):
		st.rerun()
else:
	with st.form("login_form"):
		username = st.text_input("E-mail ou usuário")
		password = st.text_input("Senha", type="password")
		submitted = st.form_submit_button("Entrar")

	if submitted:
		if not username or not password:
			st.warning("Preencha usuário e senha.")
		else:
			ok, msg = autenticar_usuario(username.strip(), password)
			if ok:
				controller = get_cookie_controller()
				controller.set("auth_user", st.session_state["user_name"], max_age=86400 * 7)
				controller.set("auth_role", st.session_state.get("user_role", ""), max_age=86400 * 7)
				st.session_state["auth"] = True
				st.success("Login realizado com sucesso.")
				st.rerun()
			else:
				st.error(msg)
