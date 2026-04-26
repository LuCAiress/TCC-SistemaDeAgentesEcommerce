import streamlit as st
from streamlit_cookies_controller import CookieController
import os

_controller = None

def get_cookie_controller():
    global _controller
    if _controller is None:
        _controller = CookieController()
    return _controller

controller = get_cookie_controller()

def logout():
    if st.session_state.get("auth"):
        if st.button("Sair", type="secondary", use_container_width=True):
            controller.remove("auth_user")
            controller.remove("auth_role")
            st.session_state.clear()
            st.rerun()
            
def get_auth_table_config():
	schema = os.getenv("AUTH_SCHEMA", "public")
	table = os.getenv("AUTH_TABLE", "usuarios")
	user_field = os.getenv("AUTH_USER_FIELD", "email")
	password_field = os.getenv("AUTH_PASSWORD_FIELD", "senha")
	role_field = os.getenv("AUTH_ROLE_FIELD", "cargo")

	# Tabela pode ter schema: ex.: public.users ou auth.users
	if not table.replace("_", "").replace(".", "").isalnum():
		st.error("Configuração de autenticação inválida para AUTH_TABLE. Use opcionalmente schema.tabela, apenas com letras, números e _.")
		st.stop()

	for value in (user_field, password_field):
		if not value.replace("_", "").replace(".", "").isalnum():
			st.error("Configuração de autenticação inválida. Verifique AUTH_USER_FIELD e AUTH_PASSWORD_FIELD no .env.")
			st.stop()

	return schema, table, user_field, password_field, role_field