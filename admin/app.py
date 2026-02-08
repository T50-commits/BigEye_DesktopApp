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
    st.markdown("**Admin Dashboard**")
    st.divider()
    st.caption(f"Environment: `{os.getenv('ENVIRONMENT', 'development')}`")

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ── Main content (redirect to Dashboard page) ──
st.markdown("# 👁️ BigEye Pro — Admin Dashboard")
st.info("👈 Use the sidebar to navigate between pages.")
st.markdown("---")
st.markdown(
    "**Pages:**\n"
    "- 📊 **Dashboard** — Today's stats, revenue, user growth\n"
    "- 👥 **Users** — Manage users, credits, suspensions\n"
    "- 🧾 **Slips** — Review top-up payment slips\n"
    "- ⚙️ **Jobs** — Monitor processing jobs\n"
    "- 🔧 **System Config** — App version, rates, prompts\n"
    "- 📋 **Audit Logs** — System event logs\n"
)
