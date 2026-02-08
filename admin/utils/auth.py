"""
BigEye Pro Admin — Simple Password Authentication
Single admin only — password stored in environment variable.
"""
import streamlit as st
import os


def check_password() -> bool:
    """Show login form and verify password. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    admin_password = os.getenv("ADMIN_PASSWORD", "admin")

    st.set_page_config(page_title="BigEye Admin — Login", page_icon="🔐", layout="centered")

    st.markdown(
        "<h1 style='text-align:center;'>🔐 BigEye Pro Admin</h1>"
        "<p style='text-align:center; color:#888;'>Enter admin password to continue</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        password = st.text_input("Password", type="password", placeholder="Enter admin password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if password == admin_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")

    return False
