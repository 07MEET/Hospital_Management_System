def load_css():
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: #f7f8fc !important;
    color: #1e293b !important;
}

/* ── Hide Streamlit default chrome ── */
footer { visibility: hidden; }
.block-container {
    padding: 1.5rem 2.5rem 3rem !important;
    max-width: 1300px !important;
}

/* ── Page Title ── */
.page-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.25rem;
    letter-spacing: -0.5px;
}
.page-subtitle {
    font-size: 0.88rem;
    color: #64748b;
    margin: 0 0 1.5rem;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0f172a !important;
    min-width: 230px !important;
    max-width: 230px !important;
}
section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #94a3b8 !important;
    border: none !important;
    text-align: left !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    width: 100% !important;
    font-weight: 400 !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #f1f5f9 !important;
}

/* ── Metric Cards — native Streamlit ── */
[data-testid="metric-container"] {
    background: white !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 1.25rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}
[data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stTimeInput > div > div > input {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
    background: #ffffff !important;
    color: #1e293b !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
    outline: none !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s !important;
    border: 1.5px solid transparent !important;
}
.stButton > button[kind="primary"] {
    background: #2563eb !important;
    color: white !important;
    border-color: #2563eb !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    color: #374151 !important;
    border-color: #d1d5db !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #f9fafb !important;
    border-color: #9ca3af !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: white !important;
    border-bottom: 2px solid #e2e8f0 !important;
    gap: 0 !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.75rem 1.25rem !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
    font-weight: 600 !important;
}

/* ── Alerts ── */
.stSuccess > div, .stError > div, .stWarning > div, .stInfo > div {
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.875rem !important;
}

/* ── Section header ── */
.section-header {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e2e8f0;
}

/* ── Card ── */
.info-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-green  { background: #dcfce7; color: #15803d; }
.badge-red    { background: #fee2e2; color: #dc2626; }
.badge-amber  { background: #fef3c7; color: #d97706; }
.badge-blue   { background: #dbeafe; color: #1d4ed8; }
.badge-gray   { background: #f1f5f9; color: #475569; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
</style>
"""