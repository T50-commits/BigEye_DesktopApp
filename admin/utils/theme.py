"""
BigEye Pro Admin — Shared Theme CSS
Import and call inject_css() at the top of every page.
"""
import streamlit as st


def inject_css():
    """Inject shared CSS theme into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
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
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

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
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }

    /* Buttons — primary */
    .stButton button[kind="primary"] {
        border-radius: 8px;
    }
    .stButton button {
        border-radius: 8px;
    }
</style>
"""
