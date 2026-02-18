"""
BigEye Pro Admin — Simple Password Authentication
Single admin only — password stored in environment variable.
"""
import streamlit as st
import os


def require_auth():
    """Call at the top of every page to block unauthenticated sidebar navigation."""
    if not st.session_state.get("authenticated"):
        st.warning("🔒 กรุณาเข้าสู่ระบบก่อนใช้งาน")
        st.stop()


def check_password() -> bool:
    """Show login form and verify password. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    admin_password = os.getenv("ADMIN_PASSWORD", "")

    st.set_page_config(page_title="BigEye Admin — เข้าสู่ระบบ", page_icon="🔐", layout="centered")

    # Block access if ADMIN_PASSWORD is not configured or is the insecure default
    if not admin_password or admin_password == "admin":
        st.markdown(
            "<h1 style='text-align:center;'>🔐 BigEye Pro Admin</h1>",
            unsafe_allow_html=True,
        )
        st.error(
            "⛔ ADMIN_PASSWORD ยังไม่ได้ตั้งค่า หรือยังเป็นค่า default\n\n"
            "กรุณาตั้ง environment variable `ADMIN_PASSWORD` ให้เป็นรหัสผ่านที่ปลอดภัยก่อนใช้งาน"
        )
        st.stop()
        return False

    st.markdown(
        "<h1 style='text-align:center;'>🔐 BigEye Pro Admin</h1>"
        "<p style='text-align:center; color:#888;'>กรอกรหัสผ่านแอดมินเพื่อดำเนินการต่อ</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        password = st.text_input("รหัสผ่าน", type="password", placeholder="กรอกรหัสผ่านแอดมิน")
        submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

    if submitted:
        if password == admin_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ รหัสผ่านไม่ถูกต้อง")

    return False
