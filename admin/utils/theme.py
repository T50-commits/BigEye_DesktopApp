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
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --bg-primary: #080c16;
        --bg-secondary: #0f1629;
        --bg-card: #1a2035;
        --bg-card-hover: #1e2642;
        --bg-input: #0f1629;
        --border: #1e293b;
        --border-light: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --accent-blue: #3b82f6;
        --accent-cyan: #06b6d4;
        --accent-green: #10b981;
        --accent-yellow: #f59e0b;
        --accent-red: #ef4444;
        --accent-purple: #8b5cf6;
        --accent-pink: #ec4899;
        --accent-orange: #f97316;
    }

    body { font-family: 'DM Sans', 'IBM Plex Sans Thai', sans-serif; }
    code, .mono { font-family: 'JetBrains Mono', monospace; }

    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Override sidebar */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .css-1d391kg { padding-top: 1rem; }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--text-secondary) !important;
        border-radius: 8px;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.12);
        color: var(--text-primary) !important;
    }

    /* Override main area */
    .main .block-container {
        padding: 2rem;
        max-width: 1400px;
    }

    /* Override dataframe */
    [data-testid="stDataFrame"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
    }

    /* Override buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent-blue);
        border-color: var(--accent-blue);
    }
    .stButton > button[kind="primary"]:hover {
        background: #2563eb;
        box-shadow: 0 0 20px rgba(59,130,246,0.15);
    }

    /* Override inputs */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea textarea {
        background: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 1px var(--accent-blue) !important;
    }

    /* Override tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text-secondary);
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
        color: white !important;
    }

    /* Override expander */
    .streamlit-expanderHeader {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        margin-bottom: 8px;
    }

    /* Override divider */
    hr { border-color: var(--border) !important; }

    /* Override metric */
    [data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 20px;
    }

    /* Override forms */
    [data-testid="stForm"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        background: var(--bg-card);
    }

    /* Headers */
    h1 { color: var(--text-primary) !important; font-weight: 800 !important; }
    h2 { color: var(--text-primary) !important; }
    h3 { color: var(--text-primary) !important; }
</style>
"""
