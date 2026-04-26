import os

import streamlit as st
import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from utils import logout

load_dotenv()

# ── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    logout()

# ── Conexão ──────────────────────────────────────────────────────

@st.cache_resource
def _get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        st.error("DATABASE_URL não definida no arquivo .env")
        return None
    return create_engine(url)


engine = _get_engine()
if engine is None:
    st.stop()

# ── Helpers ──────────────────────────────────────────────────────

def cadastrar_usuario(email: str, password: str, role: str) -> tuple[bool, str]:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (email, password, role) VALUES (:email, :password, :role)"),
                {"email": email, "password": bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"), "role": role},
            )
        return True, ""
    except Exception as e:
        msg = str(e)
        if "unique" in msg.lower() or "duplicate" in msg.lower():
            return False, "E-mail já cadastrado."
        return False, f"Erro ao cadastrar: {msg}"


def listar_usuarios() -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT email, role FROM users ORDER BY email")
            ).mappings().fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        st.error(f"Erro ao consultar usuários: {e}")
        return []


def excluir_usuario(email: str) -> tuple[bool, str]:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": email},
            )
        return True, ""
    except Exception as e:
        return False, f"Erro ao excluir: {e}"


# ── Página ──────────────────────────────────────────────────────

st.title("🛠️ Controle de Usuários")
st.divider()

# ── Cadastro ─────────────────────────────────────────────────────
st.subheader("Cadastrar novo usuário")

with st.form("form_cadastro", clear_on_submit=True):
    novo_email = st.text_input("E-mail")
    nova_senha = st.text_input("Senha", type="password")
    novo_role  = st.selectbox("Perfil", options=["user", "admin"])
    submitted  = st.form_submit_button("✅ Cadastrar", type="primary", use_container_width=True)

if submitted:
    if not novo_email.strip() or not nova_senha:
        st.warning("Preencha e-mail e senha.")
    else:
        ok, err = cadastrar_usuario(novo_email.strip(), nova_senha, novo_role)
        if ok:
            st.success(f"Usuário **{novo_email.strip()}** cadastrado com sucesso!")
        else:
            st.error(err)

st.divider()

# ── Lista de usuários ─────────────────────────────────────────────
st.subheader("Usuários cadastrados")

usuarios = listar_usuarios()
usuario_logado = st.session_state.get("user_name", "")

if not usuarios:
    st.info("Nenhum usuário cadastrado.")
else:
    col_header1, col_header2, col_header3 = st.columns([3, 1, 1])
    with col_header1:
        st.markdown("**E-mail**")
    with col_header2:
        st.markdown("**Perfil**")
    with col_header3:
        st.markdown("**Ação**")

    for u in usuarios:
        email = u["email"]
        role  = u.get("role") or "—"
        is_self     = email == usuario_logado
        confirm_key = f"confirm_del_{email}"

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(email)
        with col2:
            st.write(role)
        with col3:
            if st.session_state.get(confirm_key):
                # Altera o estado do botão para confirmação da remoção
                st.warning(f"Excluir **{email}**?")
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("✅", key=f"yes_{email}", use_container_width=True, help="Confirmar exclusão"):
                        ok, err = excluir_usuario(email)
                        st.session_state.pop(confirm_key, None)
                        if ok:
                            st.success(f"Usuário **{email}** excluído.")
                            st.rerun()
                        else:
                            st.error(err)
                with btn_col2:
                    if st.button("❌", key=f"no_{email}", use_container_width=True, help="Cancelar"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
            else:
                if st.button(
                    "🗑️ Excluir",
                    key=f"del_{email}",
                    use_container_width=True,
                    disabled=is_self,
                    help="Não é possível excluir o próprio usuário." if is_self else None,
                ):
                    st.session_state[confirm_key] = True
                    st.rerun()