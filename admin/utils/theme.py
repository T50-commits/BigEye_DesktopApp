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
    /* ═══════════════════════════════════════
       BigEye Pro Admin — Executive Dark Theme
       ═══════════════════════════════════════ */

    /* ── Root variables ── */
    :root {
        --bg-primary: #0B0F19;
        --bg-secondary: #111827;
        --bg-card: #1A2035;
        --bg-card-hover: #1F2A45;
        --border: #1E2A45;
        --border-light: #2A3A5C;
        --text-primary: #E8ECF4;
        --text-secondary: #8892A8;
        --text-dim: #4A5568;
        --accent-pink: #FF00CC;
        --accent-purple: #7B2FFF;
        --success: #00E396;
        --warning: #FEB019;
        --error: #FF4560;
        --info: #00B4D8;
        --gold: #FFD700;
    }

    /* ── Global background ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bg-primary) !important;
    }
    .main .block-container {
        padding-top: 1.2rem;
        max-width: 1400px;
    }

    /* ── Sidebar — Deep Navy gradient ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e1a 0%, #0d1526 50%, #111d35 100%) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * {
        color: var(--text-secondary) !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--border);
        color: var(--text-primary) !important;
        border-radius: 10px;
        padding: 10px 16px;
        font-weight: 500;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(135deg, rgba(255,0,204,0.08), rgba(123,47,255,0.08));
        border-color: rgba(255,0,204,0.3);
        color: var(--accent-pink) !important;
    }

    /* ── Headers ── */
    h1 {
        color: var(--text-primary) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }
    p, li, span, label, .stMarkdown {
        color: var(--text-secondary) !important;
    }

    /* ── Cards (st.metric, forms, expanders) ── */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 20px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Forms ── */
    [data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 24px !important;
    }

    /* ── Inputs ── */
    input, textarea, [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background: var(--bg-secondary) !important;
        border-color: var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 10px !important;
    }
    input:focus, textarea:focus {
        border-color: var(--accent-pink) !important;
    }

    /* ── Select / Dropdowns ── */
    [data-baseweb="select"] > div {
        background: var(--bg-secondary) !important;
        border-color: var(--border) !important;
        border-radius: 10px !important;
    }
    [data-baseweb="select"] * {
        color: var(--text-primary) !important;
    }
    [data-baseweb="popover"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="menu"] {
        background: var(--bg-card) !important;
    }
    [data-baseweb="menu"] li {
        color: var(--text-secondary) !important;
    }
    [data-baseweb="menu"] li:hover {
        background: rgba(255,0,204,0.08) !important;
        color: var(--accent-pink) !important;
    }

    /* ── Buttons ── */
    .stButton button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: 10px !important;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, rgba(255,0,204,0.1), rgba(123,47,255,0.1)) !important;
        border-color: rgba(255,0,204,0.4) !important;
        color: var(--accent-pink) !important;
    }
    /* Primary buttons — gradient */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-pink), var(--accent-purple)) !important;
        border: none !important;
        color: #fff !important;
        font-weight: 600;
    }
    .stButton button[kind="primary"]:hover {
        opacity: 0.9;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 10px;
    }
    [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
    }

    /* ── Dataframe / Tables ── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    [data-testid="stDataFrame"] table {
        background: var(--bg-card) !important;
    }
    [data-testid="stDataFrame"] th {
        background: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stDataFrame"] td {
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--bg-secondary);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border-radius: 8px;
        padding: 8px 20px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--bg-card) !important;
        color: var(--accent-pink) !important;
    }

    /* ── Dividers ── */
    hr {
        border-color: var(--border) !important;
    }

    /* ── Info/Warning/Error boxes ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    /* ── Code blocks ── */
    code {
        background: var(--bg-secondary) !important;
        color: var(--accent-pink) !important;
        border-radius: 6px;
        padding: 2px 6px;
    }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-dim) !important;
    }

    /* ── Number inputs ── */
    [data-testid="stNumberInput"] input {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
    }

    /* ── JSON viewer ── */
    .react-json-view {
        background: var(--bg-secondary) !important;
        border-radius: 10px;
        padding: 12px;
    }

    /* ── Plotly charts background ── */
    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb {
        background: var(--border-light);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
</style>
"""
