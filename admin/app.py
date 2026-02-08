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

# ── Import shared theme ──
from utils.theme import inject_css
inject_css()

# ── Sidebar ──
with st.sidebar:
    st.markdown("""
    <div style="
        text-align: center;
        padding: 16px 0 8px 0;
    ">
        <div style="
            font-size: 1.4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FF00CC, #7B2FFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        ">👁 BigEye Pro</div>
        <div style="
            font-size: 0.75rem;
            color: #4A5568;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-top: 4px;
        ">Admin Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    env = os.getenv("ENVIRONMENT", "development")
    env_color = "#00E396" if env == "production" else "#FEB019"
    st.markdown(f"""
    <div style="
        background: rgba(255,255,255,0.03);
        border: 1px solid #1E2A45;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
    ">
        <span style="
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            background: {env_color};
            margin-right: 6px;
        "></span>
        <span style="font-size:0.8rem;color:#8892A8">{env}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ── Main content ──
st.markdown("# 👁️ BigEye Pro Admin")
st.markdown("##### แผงควบคุมสำหรับผู้ดูแลระบบ — เลือกเมนูด้านซ้ายเพื่อเริ่มใช้งาน")
st.markdown("")

# Navigation cards
def _nav_card(icon: str, title: str, desc: str, color: str) -> str:
    return f"""
    <div style="
        background: linear-gradient(135deg, #1A2035 0%, #111827 100%);
        border: 1px solid #1E2A45;
        border-radius: 14px;
        padding: 24px 20px;
        margin-bottom: 12px;
        transition: all 0.15s;
        cursor: pointer;
    "
    onmouseover="this.style.borderColor='rgba(255,0,204,0.3)'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0,0,0,0.3)'"
    onmouseout="this.style.borderColor='#1E2A45'; this.style.transform='translateY(0)'; this.style.boxShadow='none'"
    >
        <div style="font-size:1.8rem;margin-bottom:10px">{icon}</div>
        <div style="font-weight:700;font-size:1.05rem;color:#E8ECF4;margin-bottom:4px">{title}</div>
        <div style="color:#8892A8;font-size:0.85rem;line-height:1.4">{desc}</div>
    </div>
    """

_pages = [
    ("📊", "แดชบอร์ด", "สถิติวันนี้ รายได้ การเติบโตผู้ใช้", "#00B4D8"),
    ("👥", "ผู้ใช้งาน", "จัดการผู้ใช้ เครดิต ระงับ/เปิดบัญชี", "#7B2FFF"),
    ("🧾", "สลิปเติมเงิน", "ตรวจสอบ อนุมัติ/ปฏิเสธสลิป", "#FEB019"),
    ("⚙️", "ตรวจสอบงาน", "ดูสถานะงาน คืนเครดิตงานค้าง", "#00E396"),
    ("🔧", "ตั้งค่าระบบ", "เวอร์ชัน อัตราเครดิต พรอมต์ คำต้องห้าม", "#FF00CC"),
    ("📋", "บันทึกระบบ", "เหตุการณ์สำคัญ ติดตามพฤติกรรม", "#8892A8"),
    ("🎁", "โปรโมชั่น", "จัดการแคมเปญ โบนัส ส่วนลด", "#FFD700"),
]

cols = st.columns(3)
for i, (icon, title, desc, color) in enumerate(_pages):
    with cols[i % 3]:
        st.markdown(_nav_card(icon, title, desc, color), unsafe_allow_html=True)
