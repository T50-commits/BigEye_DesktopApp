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
from utils.theme import inject_css
inject_css()

st.markdown("""
<style>
    .nav-card {
        background: #1a2035;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 22px 20px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .nav-card:hover {
        transform: translateY(-2px);
        border-color: #334155;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .nav-card h3 { margin: 0 0 6px 0; font-size: 1.05rem; color: #f1f5f9; }
    .nav-card p { margin: 0; color: #64748b; font-size: 0.85rem; }
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
st.markdown("# 👁️ BigEye Pro Admin")
st.markdown("##### แผงควบคุมสำหรับผู้ดูแลระบบ — เลือกเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
st.markdown("")

# Navigation cards
_pages = [
    ("📊", "แดชบอร์ด", "สถิติวันนี้ รายได้ การเติบโตผู้ใช้"),
    ("👥", "ผู้ใช้งาน", "จัดการผู้ใช้ เครดิต ระงับ/เปิดบัญชี"),
    ("🧾", "สลิปเติมเงิน", "ตรวจสอบ อนุมัติ/ปฏิเสธสลิป"),
    ("⚙️", "ตรวจสอบงาน", "ดูสถานะงาน คืนเครดิตงานค้าง"),
    ("🔧", "ตั้งค่าระบบ", "เวอร์ชัน อัตราเครดิต พรอมต์ คำต้องห้าม"),
    ("📋", "บันทึกระบบ", "เหตุการณ์สำคัญ ติดตามพฤติกรรม"),
    ("🎁", "โปรโมชั่น", "จัดการแคมเปญ โบนัส ส่วนลด"),
]

cols = st.columns(3)
for i, (icon, title, desc) in enumerate(_pages):
    with cols[i % 3]:
        st.markdown(f"""<div class="nav-card"><h3>{icon} {title}</h3><p>{desc}</p></div>""", unsafe_allow_html=True)
