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
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #111d35 100%);
    }
    [data-testid="stSidebar"] * {
        color: #c8d6e5 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        color: #fff !important;
        border-radius: 8px;
        transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.18);
    }

    /* Main */
    .block-container { padding-top: 1.5rem; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; color: #1e293b !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Headers */
    h1 { color: #0f172a !important; font-weight: 800 !important; }
    h2 { color: #1e293b !important; }

    /* Expanders */
    [data-testid="stExpander"] {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        margin-bottom: 8px;
    }

    /* Forms */
    [data-testid="stForm"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        background: #fafbfc;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }

    /* Nav card */
    .nav-card {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .nav-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .nav-card h3 { margin: 0 0 6px 0; font-size: 1.1rem; color: #1e293b; }
    .nav-card p { margin: 0; color: #64748b; font-size: 0.9rem; }
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
