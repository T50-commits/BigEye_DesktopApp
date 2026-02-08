"""
BigEye Pro — Admin Dashboard
Streamlit-based admin panel for managing users, credits, slips, and system config.
"""
import os
import streamlit as st
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

from utils.auth import check_password

# ── Authentication gate ──
if not check_password():
    st.stop()

# ── Authenticated: Configure main page ──
st.set_page_config(
    page_title="BigEye Pro Admin",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F0F23 0%, #1A1A2E 100%);
    }
    .stMetric {
        background: #16213E;
        border: 1px solid #1A3A6B;
        border-radius: 12px;
        padding: 16px;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## 👁️ BigEye Pro")
    st.markdown("**แผงควบคุมแอดมิน**")
    st.divider()
    st.caption(f"สภาพแวดล้อม: `{os.getenv('ENVIRONMENT', 'development')}`")

    st.divider()
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ── Main content ──
st.markdown("# 👁️ BigEye Pro — แผงควบคุมแอดมิน")
st.info("👈 ใช้เมนูด้านซ้ายเพื่อเปลี่ยนหน้า")
st.markdown("---")
st.markdown(
    "**หน้าต่างๆ:**\n"
    "- 📊 **แดชบอร์ด** — สถิติวันนี้, รายได้, การเติบโตผู้ใช้\n"
    "- 👥 **ผู้ใช้งาน** — จัดการผู้ใช้, เครดิต, ระงับบัญชี\n"
    "- 🧾 **สลิปเติมเงิน** — ตรวจสอบสลิปการชำระเงิน\n"
    "- ⚙️ **ตรวจสอบงาน** — ดูสถานะงานประมวลผล\n"
    "- 🔧 **ตั้งค่าระบบ** — เวอร์ชันแอป, อัตราเครดิต, พรอมต์\n"
    "- 📋 **บันทึกระบบ** — บันทึกเหตุการณ์ระบบ\n"
    "- 🎁 **โปรโมชั่น** — จัดการโปรโมชั่นและแคมเปญ\n"
)
