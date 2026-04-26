import streamlit as st
from streamlit_cookies_controller import CookieController

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