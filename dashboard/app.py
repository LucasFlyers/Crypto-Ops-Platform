"""
CryptoOps Platform Dashboard — Spacing Fix Build
- No split HTML divs around Streamlit widgets
- No gap:0 on all vertical blocks (only on nav)
- All page padding via explicit style divs per section
- Nav is pure HTML navbar + st.radio below it
"""
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import requests
import streamlit as st

st.set_page_config(
    page_title="CryptoOps",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_URL = "postgresql://neondb_owner:npg_lput5gMnSq0B@ep-square-hill-a4z4p0ij-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
API_URL = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@300;400;500&display=swap');

:root {
  --bg:     #0a0c10;
  --s1:     #0f1117;
  --s2:     #161b24;
  --b1:     #1e2738;
  --b2:     #263044;
  --t1:     #e8edf5;
  --t2:     #7a8a9e;
  --t3:     #3d4f63;
  --blue:   #3d8ef0;
  --blue2:  #5aa3ff;
  --green:  #2ecc71;
  --amber:  #f0a500;
  --red:    #e85454;
  --orange: #f07030;
  --purple: #9b72f5;
  --teal:   #20c4b0;
}

*, *::before, *::after { box-sizing: border-box; }

/* Backgrounds — specific selectors only */
html, body { background: var(--bg) !important; color: var(--t1) !important; }
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section.main,
.main .block-container { background: var(--bg) !important; }

/* Scrollbars */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--s1); }
::-webkit-scrollbar-thumb { background: var(--b2); border-radius: 2px; }

/* Kill Streamlit chrome */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu, footer,
button[data-testid="collapsedControl"],
section[data-testid="stSidebar"] { display: none !important; }

/* Layout — zero out default block padding so navbar goes edge-to-edge */
.block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }

/* Columns — gap only, no padding override that bleeds into cards */
div[data-testid="stHorizontalBlock"] { gap: 20px !important; }
div[data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }

/* Cards (st.container border=True) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--s1) !important;
    border: 1px solid var(--b1) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* Navbar merged into .topbar above */

/* ── Topbar: single unified bar — brand | nav tabs | refresh + status ── */
.topbar {
    display: flex; align-items: center;
    background: var(--s1); border-bottom: 1px solid var(--b1);
    padding: 0; height: 52px; width: 100%;
}
.topbar-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 0 20px; border-right: 1px solid var(--b1);
    height: 100%; flex-shrink: 0;
}
.topbar-icon {
    width: 26px; height: 26px; border-radius: 6px;
    background: linear-gradient(135deg, #3d8ef0, #9b72f5);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; color: #fff; font-weight: 700;
}
.topbar-title { font-family: 'IBM Plex Sans', sans-serif; font-size: 14px; font-weight: 600; color: #e8edf5; line-height: 1.2; }
.topbar-sub   { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3d4f63; letter-spacing: .08em; }
.topbar-nav   { display: flex; align-items: center; gap: 2px; padding: 0 12px; flex: 1; height: 100%; }
.nav-item {
    height: 32px; padding: 0 14px; border-radius: 5px;
    font-family: 'IBM Plex Sans', sans-serif; font-size: 12px; font-weight: 400;
    color: #7a8a9e; background: transparent; border: none;
    text-decoration: none; display: inline-flex; align-items: center;
    transition: background .12s, color .12s; white-space: nowrap; cursor: pointer;
}
.nav-item:hover  { background: rgba(255,255,255,0.05); color: #e8edf5; }
.nav-item.active { background: rgba(61,142,240,0.14); color: #5aa3ff; font-weight: 600; }
.topbar-right {
    display: flex; align-items: center; gap: 16px;
    padding: 0 20px; border-left: 1px solid var(--b1);
    height: 100%; flex-shrink: 0;
}
.refresh-btn {
    height: 28px; padding: 0 12px; border-radius: 5px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: #7a8a9e; background: transparent;
    border: 1px solid var(--b1); text-decoration: none;
    display: inline-flex; align-items: center; gap: 5px;
    transition: border-color .12s, color .12s; white-space: nowrap;
}
.refresh-btn:hover { border-color: #3d8ef0; color: #5aa3ff; }
.api-badge { display: flex; align-items: center; gap: 6px; font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: .1em; }
.api-dot   { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.topbar-ts { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3d4f63; }

/* Radio inside tabbar */
div[data-testid="stRadio"] { margin: 0 !important; padding: 0 !important; }
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    display: flex !important; flex-direction: row !important;
    gap: 2px !important; align-items: center !important; flex-wrap: nowrap !important;
}
div[data-testid="stRadio"] > div > label {
    padding: 6px 16px !important; border-radius: 4px !important;
    font-size: 12px !important; font-weight: 400 !important; color: #7a8a9e !important;
    cursor: pointer !important; white-space: nowrap !important;
    margin: 0 !important; border: none !important; background: transparent !important;
    transition: background .12s, color .12s !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: rgba(255,255,255,0.05) !important; color: #e8edf5 !important;
}
div[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }
div[data-testid="stRadio"] [aria-checked="true"] {
    background: rgba(61,142,240,0.14) !important;
    color: #5aa3ff !important; font-weight: 600 !important;
}

/* Page title block */
.page-title { padding: 22px 28px 16px; border-bottom: 1px solid var(--b1); margin-bottom: 0; }
.page-title h2 { margin: 0; font-family: 'IBM Plex Sans', sans-serif; font-size: 18px; font-weight: 600; color: #e8edf5; }
.page-title p  { margin: 3px 0 0; font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #3d4f63; letter-spacing: .08em; text-transform: uppercase; }

/* Suppress Streamlit's auto-anchor icon on headings */
h1 a, h2 a, h3 a { display: none !important; }

/* ── Page content area: consistent horizontal padding on column rows ── */
[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
    padding-left: 28px !important;
    padding-right: 28px !important;
}
/* But NOT inside cards */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
    padding-left: 0 !important;
    padding-right: 0 !important;
}

/* Section header inside card */
.section-hdr {
    display: flex; align-items: center; gap: 8px;
    padding: 14px 18px 12px; border-bottom: 1px solid var(--b1);
}
.section-hdr-bar  { width: 3px; height: 13px; border-radius: 2px; flex-shrink: 0; }
.section-hdr-text { font-family: 'IBM Plex Sans', sans-serif; font-size: 12px; font-weight: 600; color: #c8d4e4; }

/* KPI cards */
.kpi-card   { background: var(--s1); border: 1px solid var(--b1); border-radius: 9px; padding: 16px 18px 14px; position: relative; overflow: hidden; height: 100%; }
.kpi-accent { position: absolute; top: 0; left: 0; right: 0; height: 2px; border-radius: 9px 9px 0 0; }
.kpi-label  { font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #3d4f63; margin-bottom: 8px; }
.kpi-value  { font-family: 'IBM Plex Mono', monospace; font-size: 30px; line-height: 1; font-weight: 400; }
.kpi-delta  { font-family: 'IBM Plex Mono', monospace; font-size: 10px; margin-top: 6px; }

/* Buttons — general */
div[data-testid="stButton"] > button {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 13px !important; font-weight: 500 !important;
    border-radius: 6px !important; transition: all .15s !important;
}

/* Action buttons */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #3d8ef0 !important; border: none !important; color: #fff !important; font-weight: 600 !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background: #5aa3ff !important; }
div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; border: 1px solid #263044 !important; color: #7a8a9e !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover { border-color: #3d8ef0 !important; color: #5aa3ff !important; }

/* Inputs */
.stTextInput input, .stTextArea textarea {
    background: #161b24 !important; border: 1px solid #1e2738 !important;
    border-radius: 6px !important; color: #e8edf5 !important;
    font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #3d8ef0 !important; box-shadow: 0 0 0 3px rgba(61,142,240,.12) !important; outline: none !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label {
    font-size: 10px !important; font-weight: 600 !important; letter-spacing: .1em !important;
    text-transform: uppercase !important; color: #3d4f63 !important; font-family: 'IBM Plex Mono', monospace !important;
}
.stSelectbox > div > div { background: #161b24 !important; border: 1px solid #1e2738 !important; border-radius: 6px !important; color: #e8edf5 !important; }

/* DataFrame */
[data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden !important; }

/* Metrics */
[data-testid="stMetric"] label { font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important; letter-spacing: .1em !important; text-transform: uppercase !important; color: #3d4f63 !important; }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 22px !important; color: #e8edf5 !important; }

/* Footer */
.footer { text-align: center; padding: 32px 0 28px; margin-top: 8px; border-top: 1px solid #1e2738; }
.footer-copy   { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #1e2738; letter-spacing: .1em; margin-bottom: 6px; }
.footer-credit { font-family: 'IBM Plex Sans', sans-serif; font-size: 11px; color: #3d4f63; }
.footer-credit a { color: #3d8ef0; text-decoration: none; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def qdf(sql: str, params=None) -> pd.DataFrame:
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"DB error: {e}")
        return pd.DataFrame()

def qval(sql: str, params=None) -> int:
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(sql, params)
        r = cur.fetchone()
        cur.close(); conn.close()
        return int(r[0]) if r and r[0] is not None else 0
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# CHART CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
_BG    = "#0f1117"
_GRID  = "#1a2030"
_MONO  = "IBM Plex Mono, monospace"
_DIM   = "#7a8a9e"
_LIGHT = "#c8d4e4"
NOBAR  = {"displayModeBar": False}

def base_layout(h=260, legend=False, **extra):
    return dict(
        plot_bgcolor=_BG, paper_bgcolor=_BG, height=h, showlegend=legend,
        margin=dict(l=8, r=20, t=12, b=8),
        font=dict(family=_MONO, size=11, color=_DIM),
        **extra,
    )

def empty_chart(msg="No data yet"):
    st.markdown(
        f'<p style="color:#3d4f63;font-size:13px;padding:32px 0;text-align:center;'
        f'font-family:IBM Plex Mono,monospace;">{msg}</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def page_title(title: str, subtitle: str):
    st.markdown(
        f'<div class="page-title"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )

def section_hdr(text: str, accent: str = "#3d8ef0"):
    st.markdown(
        f'<div class="section-hdr">'
        f'<div class="section-hdr-bar" style="background:{accent};"></div>'
        f'<span class="section-hdr-text">{text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

def kpi_strip(items):
    cols = st.columns(len(items))
    for col, (label, value, delta, dc, accent) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-accent" style="background:{accent};"></div>'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value" style="color:{accent};">{value}</div>'
                f'<div class="kpi-delta" style="color:{dc};">{delta}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

def sp(px=20):
    st.markdown(f'<div style="height:{px}px;"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION — query_params driven so the entire header is pure HTML (no gaps)
# ─────────────────────────────────────────────────────────────────────────────
PAGES = ["Overview", "Submit Ticket", "Fraud Monitor", "All Tickets"]
PAGE_KEYS = {"overview": "Overview", "submit": "Submit Ticket",
             "fraud": "Fraud Monitor", "tickets": "All Tickets"}
PAGE_SLUGS = {v: k for k, v in PAGE_KEYS.items()}

# Read page from URL query param (set via JS onclick in the nav HTML)
_qp = st.query_params.get("p", "overview")
page = PAGE_KEYS.get(_qp, "Overview")

# API status
_api_ok = False
try:
    _r = requests.get(f"{API_URL}/health", timeout=2)
    _api_ok = _r.status_code == 200
except Exception:
    pass
_dot = "#2ecc71" if _api_ok else "#e85454"
_lbl = "ONLINE"  if _api_ok else "OFFLINE"
_ts  = datetime.utcnow().strftime("%Y-%m-%d  %H:%M")

def _nav_item(label, slug, current_slug):
    cls = "nav-item active" if slug == current_slug else "nav-item"
    return f'<a class="{cls}" href="?p={slug}">{label}</a>'

_cur = PAGE_SLUGS.get(page, "overview")

# ── Single HTML block: brand + nav tabs + refresh + API status ────────────────
# This is ONE st.markdown call — zero Streamlit elements = zero Streamlit gaps
st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-icon">&#x2B21;</div>
    <div>
      <div class="topbar-title">CryptoOps</div>
      <div class="topbar-sub">PLATFORM v1.0</div>
    </div>
  </div>

  <nav class="topbar-nav">
    {_nav_item("Overview",      "overview", _cur)}
    {_nav_item("Submit Ticket", "submit",   _cur)}
    {_nav_item("Fraud Monitor", "fraud",    _cur)}
    {_nav_item("All Tickets",   "tickets",  _cur)}
  </nav>

  <div class="topbar-right">
    <a class="refresh-btn" href="?p={_cur}">&#x21BB; Refresh</a>
    <div class="api-badge">
      <div class="api-dot" style="background:{_dot};box-shadow:0 0 5px {_dot};"></div>
      <span style="color:{_dot};">API {_lbl}</span>
    </div>
    <div class="topbar-ts">{_ts} UTC</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    page_title("Operations Overview", "real-time platform monitoring")

    total   = qval("SELECT COUNT(*) FROM tickets")
    res     = qval("SELECT COUNT(*) FROM routing WHERE resolved=true")
    open_t  = qval("SELECT COUNT(*) FROM routing WHERE resolved=false")
    t24h    = qval("SELECT COUNT(*) FROM tickets WHERE created_at >= NOW() - INTERVAL '24 hours'")
    high_p  = qval("SELECT COUNT(*) FROM classifications WHERE priority IN ('critical','high')")
    flags   = qval("SELECT COUNT(*) FROM fraud_flags")
    wallets = qval("SELECT COUNT(DISTINCT wallet_address) FROM fraud_flags")
    crit_fr = qval("SELECT COUNT(*) FROM fraud_flags WHERE flag_score >= 0.7")

    kpi_strip([
        ("Total Tickets",  total,   f"↑ {t24h} last 24 h", "#7a8a9e", "#3d8ef0"),
        ("Resolved",       res,     f"{open_t} still open", "#7a8a9e", "#2ecc71"),
        ("High Priority",  high_p,  "Needs attention",      "#f0a500", "#f0a500"),
        ("Fraud Flags",    flags,   f"{wallets} wallets",   "#e85454", "#e85454"),
        ("Critical Fraud", crit_fr, "Score >= 0.70",        "#e85454", "#9b72f5"),
    ])
    sp(24)

    # Charts row 1
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            section_hdr("Ticket Pipeline", "#3d8ef0")
            df_pipe = qdf("SELECT status, COUNT(*) as n FROM tickets GROUP BY status ORDER BY n DESC")
            if not df_pipe.empty:
                sc = {"pending":"#3d4f63","classifying":"#9b72f5","classified":"#3d8ef0",
                      "fraud_checking":"#f0a500","fraud_checked":"#20c4b0",
                      "routed":"#2ecc71","resolved":"#2ecc71",
                      "classification_error":"#e85454","routing_error":"#e85454"}
                fig = go.Figure(go.Bar(
                    x=df_pipe["n"], y=df_pipe["status"], orientation="h",
                    marker_color=[sc.get(s,"#3d4f63") for s in df_pipe["status"]],
                    marker_line_width=0, text=df_pipe["n"], textposition="outside",
                    textfont=dict(family=_MONO, size=12, color=_LIGHT),
                    hovertemplate="<b>%{y}</b>: %{x} tickets<extra></extra>",
                ))
                fig.update_layout(**base_layout(h=240))
                fig.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                 tickfont=dict(family=_MONO, size=11, color=_DIM), title="Count")
                fig.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                 tickfont=dict(family=_MONO, size=12, color=_LIGHT), title="")
                st.plotly_chart(fig, use_container_width=True, config=NOBAR)
            else:
                empty_chart("No tickets yet")

    with col_b:
        with st.container(border=True):
            section_hdr("Priority Breakdown", "#f0a500")
            df_pri = qdf("""
                SELECT priority, COUNT(*) as n FROM classifications GROUP BY priority
                ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                                       WHEN 'medium' THEN 3 ELSE 4 END
            """)
            if not df_pri.empty:
                pc = {"critical":"#e85454","high":"#f07030","medium":"#f0a500","low":"#2ecc71"}
                total_c = int(df_pri["n"].sum())
                fig2 = go.Figure(go.Pie(
                    labels=df_pri["priority"], values=df_pri["n"], hole=0.56,
                    marker_colors=[pc.get(p,"#3d4f63") for p in df_pri["priority"]],
                    textinfo="label+percent",
                    textfont=dict(family=_MONO, size=11, color=_LIGHT),
                    hovertemplate="<b>%{label}</b><br>%{value} tickets · %{percent}<extra></extra>",
                ))
                fig2.update_layout(
                    **base_layout(h=240),
                    annotations=[dict(text=f"<b>{total_c}</b>", x=0.5, y=0.5, showarrow=False,
                                      font=dict(family=_MONO, size=24, color=_LIGHT))],
                )
                st.plotly_chart(fig2, use_container_width=True, config=NOBAR)
            else:
                empty_chart("No classification data yet")
    sp(20)

    # Charts row 2
    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            section_hdr("Issue Categories", "#9b72f5")
            df_cat = qdf("""
                SELECT category, COUNT(*) as n, ROUND(AVG(fraud_score)::numeric,2) as avg_fraud
                FROM classifications GROUP BY category ORDER BY n DESC
            """)
            if not df_cat.empty:
                pal = ["#3d8ef0","#9b72f5","#20c4b0","#2ecc71","#f0a500","#f07030","#e85454"]
                fig3 = go.Figure()
                for i, row in df_cat.iterrows():
                    fig3.add_trace(go.Bar(
                        x=[str(row["category"])], y=[row["n"]], name=str(row["category"]),
                        marker_color=pal[i % len(pal)], marker_line_width=0,
                        text=[str(int(row["n"]))], textposition="outside",
                        textfont=dict(family=_MONO, size=12, color=_LIGHT),
                        hovertemplate=f"<b>{row['category']}</b><br>Tickets: {row['n']}<br>Avg Fraud: {row['avg_fraud']:.2f}<extra></extra>",
                    ))
                fig3.update_layout(**base_layout(h=240))
                fig3.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                  tickfont=dict(family=_MONO, size=10, color=_DIM), title="")
                fig3.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                  tickfont=dict(family=_MONO, size=11, color=_DIM), title="Tickets")
                st.plotly_chart(fig3, use_container_width=True, config=NOBAR)
            else:
                empty_chart("No category data yet")

    with col_d:
        with st.container(border=True):
            section_hdr("Team Workload", "#2ecc71")
            df_wl = qdf("""
                SELECT assigned_team,
                       COUNT(*) FILTER (WHERE resolved=false) as open,
                       COUNT(*) FILTER (WHERE resolved=true)  as done
                FROM routing GROUP BY assigned_team ORDER BY open DESC
            """)
            if not df_wl.empty:
                lm = {"compliance_team":"Compliance","fraud_investigation":"Fraud",
                      "security_team":"Security","technical_operations":"Tech Ops","customer_support":"Support"}
                df_wl["label"] = df_wl["assigned_team"].map(lambda t: lm.get(t, t))
                fig4 = go.Figure()
                fig4.add_trace(go.Bar(name="Open", x=df_wl["label"], y=df_wl["open"],
                    marker_color="#e85454", marker_line_width=0,
                    text=df_wl["open"], textposition="inside",
                    textfont=dict(family=_MONO, size=11, color="#fff")))
                fig4.add_trace(go.Bar(name="Resolved", x=df_wl["label"], y=df_wl["done"],
                    marker_color="#2ecc71", marker_line_width=0,
                    text=df_wl["done"], textposition="inside",
                    textfont=dict(family=_MONO, size=11, color="#fff")))
                fig4.update_layout(
                    **base_layout(h=240, legend=True, barmode="stack"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3,
                                font=dict(family=_MONO, size=11, color=_DIM)),
                )
                fig4.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                  tickfont=dict(family=_MONO, size=11, color=_LIGHT), title="")
                fig4.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                  tickfont=dict(family=_MONO, size=11, color=_DIM), title="Tickets")
                st.plotly_chart(fig4, use_container_width=True, config=NOBAR)
            else:
                empty_chart("No routing data yet")
    sp(20)

    # Recent tickets
    with st.container(border=True):
        section_hdr("Recent Tickets", "#20c4b0")
        df_rec = qdf("""
            SELECT t.id::text as id, t.user_id, t.status,
                   c.category, c.priority,
                   ROUND(c.fraud_score::numeric,2) as fraud_score,
                   r.assigned_team, r.resolved,
                   TO_CHAR(t.created_at,'MM-DD HH24:MI') as created
            FROM tickets t
            LEFT JOIN classifications c ON c.ticket_id = t.id
            LEFT JOIN routing         r ON r.ticket_id = t.id
            ORDER BY t.created_at DESC LIMIT 10
        """)
        if not df_rec.empty:
            df_rec["id"] = df_rec["id"].apply(lambda x: x[:8] + "…")
            st.dataframe(df_rec, use_container_width=True, hide_index=True,
                column_config={
                    "id":            st.column_config.TextColumn("ID", width=90),
                    "user_id":       st.column_config.TextColumn("USER", width=90),
                    "status":        st.column_config.TextColumn("STATUS", width=130),
                    "category":      st.column_config.TextColumn("CATEGORY", width=170),
                    "priority":      st.column_config.TextColumn("PRIORITY", width=90),
                    "fraud_score":   st.column_config.ProgressColumn("FRAUD", min_value=0, max_value=1, width=120),
                    "assigned_team": st.column_config.TextColumn("TEAM", width=165),
                    "resolved":      st.column_config.CheckboxColumn("done", width=55),
                    "created":       st.column_config.TextColumn("CREATED", width=105),
                })
        else:
            empty_chart("No tickets yet — submit one on the Submit Ticket page")
    sp(32)


# ═════════════════════════════════════════════════════════════════════════════
# SUBMIT TICKET
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Submit Ticket":
    page_title("Submit Ticket", "create and submit operational tickets for testing")
    sp(20)

    col_form, col_guide = st.columns([11, 7])

    with col_form:
        with st.container(border=True):
            section_hdr("New Ticket", "#3d8ef0")
            st.markdown('<div style="padding:12px 18px 20px;">', unsafe_allow_html=True)

            st.markdown(
                '<p style="font-family:IBM Plex Mono,monospace;font-size:9px;letter-spacing:.14em;'
                'text-transform:uppercase;color:#3d4f63;margin:0 0 6px;">Quick Scenario</p>',
                unsafe_allow_html=True,
            )
            scenario = st.selectbox("scenario_sel", [
                "— blank form —",
                "Pending Withdrawal Low Risk",
                "Wallet Account Access Medium Risk",
                "Unauthorized Fund Transfer High Risk",
                "Transaction Failure Technical",
                "Suspicious Transaction Pattern",
            ], label_visibility="collapsed")

            ts = int(time.time())
            uid_v = wall_v = tx_v = msg_v = ""
            if "Withdrawal" in scenario:
                uid_v="USR-1042"; wall_v="0x82fa4b3e2a9dc99d21aa0000f8c7e8b192837465"; tx_v=f"TX-{ts}"
                msg_v=("My withdrawal of 2.5 ETH submitted 8 hours ago has not arrived. "
                       "The transaction shows as processing but the funds have not reached "
                       "my external wallet. Please investigate urgently.")
            elif "Wallet" in scenario:
                uid_v="USR-2891"; wall_v="0xabcdef1234567890abcdef1234567890abcdef12"
                msg_v=("I cannot access my wallet. Every login attempt returns an authentication "
                       "error. I have not changed my password and believe my account credentials "
                       "may have been compromised.")
            elif "Unauthorized" in scenario:
                uid_v="USR-9912"; wall_v="0xdeadbeef1234567890abcdef1234567890abcdef"; tx_v=f"TX-{ts}"
                msg_v=("URGENT: Three large unauthorized transfers totalling 18.4 ETH were made "
                       "from my wallet in the last 2 hours. I did not authorize any of these. "
                       "The destination address is entirely unknown to me. This is theft.")
            elif "Transaction" in scenario:
                uid_v="USR-3344"; wall_v="0x1234567890abcdef1234567890abcdef12345678"; tx_v=f"TX-{ts}"
                msg_v=("My transaction fails every attempt with error code 0x500. "
                       "Gas fees are being deducted each time (~$45 total wasted) but "
                       "the transaction never confirms on-chain. I have retried five times.")
            elif "Suspicious" in scenario:
                uid_v="USR-7821"; wall_v="0xfedcba9876543210fedcba9876543210fedcba98"; tx_v=f"TX-{ts}"
                msg_v=("I noticed 12 small outbound transactions (0.001 ETH each) to an address "
                       "I do not recognize. The pattern resembles a probing attack before a larger theft.")

            sp(8)
            fc1, fc2 = st.columns(2)
            with fc1:
                uid  = st.text_input("User ID *", value=uid_v, placeholder="USR-0001")
            with fc2:
                txid = st.text_input("Transaction ID", value=tx_v, placeholder="TX-000000  (optional)")
            wall = st.text_input("Wallet Address", value=wall_v, placeholder="0x…  (optional)")
            msg  = st.text_area("Issue Description *", value=msg_v, height=155,
                placeholder="Describe the problem in detail. Include amounts, timings, error codes and context.")
            sp(8)
            b1, b2 = st.columns([3, 1])
            with b1:
                submitted = st.button("Submit Ticket  →", type="primary", use_container_width=True)
            with b2:
                if st.button("Clear", use_container_width=True):
                    st.rerun()

            if submitted:
                if not uid.strip():
                    st.error("User ID is required.")
                elif len(msg.strip()) < 10:
                    st.error("Issue description must be at least 10 characters.")
                else:
                    with st.spinner("Submitting to API…"):
                        payload = {"user_id": uid.strip(), "message": msg.strip()}
                        if wall.strip(): payload["wallet_address"] = wall.strip()
                        if txid.strip(): payload["transaction_id"] = txid.strip()
                        try:
                            resp = requests.post(f"{API_URL}/api/v1/tickets", json=payload, timeout=10)
                            data = resp.json()
                            if resp.status_code in (200, 202):
                                tid = data.get("ticket_id","—")
                                if data.get("status") == "already_exists":
                                    st.warning(f"Ticket already exists for this TX ID: `{tid}`")
                                else:
                                    st.success(f"Ticket submitted — ID: `{tid}`\n\nThe AI pipeline will classify, fraud-score, and route it within seconds.")
                            else:
                                st.error(f"Submission failed: {data.get('detail','Unknown error')}")
                        except requests.exceptions.ConnectionError:
                            st.error("Cannot connect to API — is the server running on port 8000?")
                        except Exception as ex:
                            st.error(f"Unexpected error: {ex}")
            st.markdown('</div>', unsafe_allow_html=True)

    with col_guide:
        with st.container(border=True):
            section_hdr("AI Processing Pipeline", "#9b72f5")
            st.markdown('<div style="padding:12px 0 8px;">', unsafe_allow_html=True)
            steps = [
                ("#3d8ef0","1","Ingestion",        "Ticket stored in PostgreSQL, status set to pending"),
                ("#9b72f5","2","AI Classification", "GPT-4o assigns category, priority and fraud score 0–1"),
                ("#f0a500","3","Fraud Detection",   "Rule engine checks wallet history, tx frequency, linked flags"),
                ("#2ecc71","4","Routing",           "Auto-assigned to compliance, fraud, security, tech ops or support"),
            ]
            for i, (color, num, title, desc) in enumerate(steps):
                connector = f'<div style="width:1px;height:10px;background:#1e2738;margin:0 0 0 27px;"></div>' if i < 3 else ""
                st.markdown(
                    f'<div style="display:flex;gap:10px;align-items:flex-start;padding:3px 18px;">'
                    f'<div style="min-width:20px;height:20px;border-radius:50%;background:{color};'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'font-family:IBM Plex Mono,monospace;font-size:9px;font-weight:700;color:#000;flex-shrink:0;">{num}</div>'
                    f'<div style="padding-bottom:2px;">'
                    f'<div style="font-family:IBM Plex Sans,sans-serif;font-size:12px;font-weight:600;color:#c8d4e4;">{title}</div>'
                    f'<div style="font-size:11px;color:#7a8a9e;margin-top:2px;line-height:1.5;">{desc}</div>'
                    f'</div></div>{connector}',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

        sp(16)

        with st.container(border=True):
            section_hdr("Routing Rules", "#f0a500")
            rules = [
                ("#e85454","Fraud score >= 0.70",     "Compliance"),
                ("#f07030","Category: fraud_report",  "Compliance"),
                ("#f07030","Category: suspicious_tx", "Fraud Invest."),
                ("#f0a500","Wallet / account access",  "Security"),
                ("#3d8ef0","Transaction failures",     "Tech Ops"),
                ("#2ecc71","All other / low priority", "Support"),
            ]
            for i, (color, cond, team) in enumerate(rules):
                bb = "border-bottom:1px solid #1e2738;" if i < 5 else ""
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 18px;{bb}">'
                    f'<span style="font-family:IBM Plex Mono,monospace;font-size:10px;color:{color};">{cond}</span>'
                    f'<span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#3d4f63;white-space:nowrap;margin-left:10px;">{team}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    sp(32)


# ═════════════════════════════════════════════════════════════════════════════
# FRAUD MONITOR
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Fraud Monitor":
    page_title("Fraud Monitor", "wallet risk analysis · flag intelligence")

    total_fl = qval("SELECT COUNT(*) FROM fraud_flags")
    flagged  = qval("SELECT COUNT(DISTINCT wallet_address) FROM fraud_flags")
    crit_fl  = qval("SELECT COUNT(*) FROM fraud_flags WHERE flag_score >= 0.7")
    fl_24h   = qval("SELECT COUNT(*) FROM fraud_flags WHERE created_at >= NOW() - INTERVAL '24 hours'")

    kpi_strip([
        ("Total Flags",      total_fl, "All time",          "#7a8a9e", "#e85454"),
        ("Flagged Wallets",  flagged,  "Unique addresses",  "#7a8a9e", "#f07030"),
        ("Critical >= 0.70", crit_fl,  "Immediate action",  "#e85454", "#e85454"),
        ("Last 24 Hours",    fl_24h,   "New flags",         "#f0a500", "#f0a500"),
    ])
    sp(24)

    col_fl, col_hr = st.columns(2)
    with col_fl:
        with st.container(border=True):
            section_hdr("Flag Score by Type", "#e85454")
            df_ft = qdf("""
                SELECT flag_type, COUNT(*) as n, ROUND(AVG(flag_score)::numeric,3) as avg_score
                FROM fraud_flags GROUP BY flag_type ORDER BY avg_score DESC
            """)
            if not df_ft.empty:
                scores = df_ft["avg_score"].tolist()
                fig_f = go.Figure(go.Bar(
                    x=scores, y=df_ft["flag_type"].tolist(), orientation="h",
                    marker=dict(color=scores,
                                colorscale=[[0,"#2a0e0e"],[0.4,"#8b1a1a"],[1,"#e85454"]],
                                cmin=0, cmax=1, line_width=0),
                    text=[f"{v:.2f}" for v in scores], textposition="outside",
                    textfont=dict(family=_MONO, size=12, color=_LIGHT),
                    customdata=df_ft["n"].tolist(),
                    hovertemplate="<b>%{y}</b><br>Avg Score: %{x:.3f}<br>Count: %{customdata}<extra></extra>",
                ))
                fig_f.update_layout(**base_layout(h=220))
                fig_f.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                   tickfont=dict(family=_MONO, size=11, color=_DIM),
                                   range=[0,1.25], title="Average Score", tickformat=".1f")
                fig_f.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, linecolor=_GRID,
                                   tickfont=dict(family=_MONO, size=12, color=_LIGHT), title="")
                st.plotly_chart(fig_f, use_container_width=True, config=NOBAR)
                st.dataframe(df_ft, use_container_width=True, hide_index=True,
                    column_config={
                        "flag_type": st.column_config.TextColumn("FLAG TYPE"),
                        "n":         st.column_config.NumberColumn("COUNT", width=70),
                        "avg_score": st.column_config.ProgressColumn("AVG SCORE", min_value=0, max_value=1),
                    })
            else:
                empty_chart("No fraud flags recorded yet")

    with col_hr:
        with st.container(border=True):
            section_hdr("High-Risk Flags  ·  Score >= 0.40", "#f07030")
            df_hr = qdf("""
                SELECT wallet_address, flag_type,
                       ROUND(flag_score::numeric,2) as score,
                       LEFT(evidence::text,55)||'…' as evidence,
                       TO_CHAR(created_at,'MM-DD HH24:MI') as time
                FROM fraud_flags WHERE flag_score >= 0.4
                ORDER BY created_at DESC LIMIT 25
            """)
            if not df_hr.empty:
                df_hr["wallet_address"] = df_hr["wallet_address"].apply(
                    lambda w: w[:10]+"…"+w[-6:] if len(str(w))>18 else w)
                st.dataframe(df_hr, use_container_width=True, hide_index=True, height=420,
                    column_config={
                        "wallet_address": st.column_config.TextColumn("WALLET"),
                        "flag_type":      st.column_config.TextColumn("TYPE"),
                        "score":          st.column_config.ProgressColumn("SCORE", min_value=0, max_value=1),
                        "evidence":       st.column_config.TextColumn("EVIDENCE"),
                        "time":           st.column_config.TextColumn("TIME", width=90),
                    })
            else:
                empty_chart("No high-risk flags found")
    sp(20)

    with st.container(border=True):
        section_hdr("Wallet Intelligence Lookup", "#f0a500")
        st.markdown('<div style="padding:12px 18px 18px;">', unsafe_allow_html=True)
        lk1, lk2 = st.columns([5, 1])
        with lk1:
            w_in = st.text_input("wallet_lookup", label_visibility="collapsed",
                placeholder="0x…  enter wallet address to look up its full history")
        with lk2:
            do_look = st.button("Look Up", use_container_width=True)
        if do_look and w_in.strip():
            w  = w_in.strip()
            wf = qdf("SELECT flag_type, ROUND(flag_score::numeric,2) as score, evidence, TO_CHAR(created_at,'YYYY-MM-DD HH24:MI') as time FROM fraud_flags WHERE wallet_address = %s ORDER BY created_at DESC", (w,))
            wt = qdf("SELECT t.id::text as ticket_id, t.user_id, t.status, c.category, c.priority, ROUND(c.fraud_score::numeric,2) as fraud_score FROM tickets t LEFT JOIN classifications c ON c.ticket_id = t.id WHERE t.wallet_address = %s ORDER BY t.created_at DESC", (w,))
            m1, m2, m3 = st.columns(3)
            m1.metric("Fraud Flags", len(wf))
            m2.metric("Tickets", len(wt))
            m3.metric("Max Score", f"{wf['score'].max():.2f}" if not wf.empty else "0.00")
            if not wf.empty:
                st.markdown("**Fraud Flags**")
                st.dataframe(wf, use_container_width=True, hide_index=True,
                    column_config={"score": st.column_config.ProgressColumn("SCORE", min_value=0, max_value=1)})
            if not wt.empty:
                st.markdown("**Associated Tickets**")
                st.dataframe(wt, use_container_width=True, hide_index=True)
            if wf.empty and wt.empty:
                st.success("No history found for this wallet address.")
        st.markdown('</div>', unsafe_allow_html=True)
    sp(32)


# ═════════════════════════════════════════════════════════════════════════════
# ALL TICKETS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "All Tickets":
    page_title("All Tickets", "full registry · filter by status, priority or team")
    sp(20)

    with st.container(border=True):
        section_hdr("Filters", "#7a8a9e")
        st.markdown('<div style="padding:12px 18px 18px;">', unsafe_allow_html=True)
        fa, fb, fc = st.columns(3)
        with fa:
            sf = st.selectbox("Status",   ["All","pending","classified","fraud_checked","routed","resolved","classification_error"])
        with fb:
            pf = st.selectbox("Priority", ["All","critical","high","medium","low"])
        with fc:
            tf = st.selectbox("Team",     ["All","compliance_team","fraud_investigation","security_team","technical_operations","customer_support"])
        sp(16)

    where_parts, params = [], []
    if sf != "All": where_parts.append("t.status = %s");        params.append(sf)
    if pf != "All": where_parts.append("c.priority = %s");      params.append(pf)
    if tf != "All": where_parts.append("r.assigned_team = %s"); params.append(tf)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    df_all = qdf(f"""
        SELECT t.id::text as ticket_id, t.user_id,
               CASE WHEN t.wallet_address IS NOT NULL
                    THEN SUBSTRING(t.wallet_address,1,8)||'…'||SUBSTRING(t.wallet_address, LENGTH(t.wallet_address)-4)
                    ELSE '—' END AS wallet,
               COALESCE(t.transaction_id,'—') AS tx_id,
               t.status, c.category, c.priority,
               ROUND(c.fraud_score::numeric,2) AS fraud_score,
               r.assigned_team, r.severity_level, r.resolved,
               LEFT(t.message,70)||CASE WHEN LENGTH(t.message)>70 THEN '…' ELSE '' END AS message,
               TO_CHAR(t.created_at,'YYYY-MM-DD HH24:MI') AS created
        FROM tickets t
        LEFT JOIN classifications c ON c.ticket_id = t.id
        LEFT JOIN routing         r ON r.ticket_id = t.id
        {where_sql}
        ORDER BY t.created_at DESC LIMIT 100
    """, params=params if params else None)

    with st.container(border=True):
        section_hdr(f"Results  ·  {len(df_all)} ticket(s)", "#20c4b0")
        if not df_all.empty:
            df_all["ticket_id"] = df_all["ticket_id"].apply(lambda x: x[:8]+"…")
            st.dataframe(df_all, use_container_width=True, hide_index=True, height=540,
                column_config={
                    "ticket_id":     st.column_config.TextColumn("ID", width=90),
                    "user_id":       st.column_config.TextColumn("USER", width=85),
                    "wallet":        st.column_config.TextColumn("WALLET", width=130),
                    "tx_id":         st.column_config.TextColumn("TX ID", width=110),
                    "status":        st.column_config.TextColumn("STATUS", width=125),
                    "category":      st.column_config.TextColumn("CATEGORY", width=170),
                    "priority":      st.column_config.TextColumn("PRIORITY", width=90),
                    "fraud_score":   st.column_config.ProgressColumn("FRAUD", min_value=0, max_value=1, width=110),
                    "assigned_team": st.column_config.TextColumn("TEAM", width=165),
                    "severity_level":st.column_config.TextColumn("SEVERITY", width=90),
                    "resolved":      st.column_config.CheckboxColumn("done", width=55),
                    "message":       st.column_config.TextColumn("MESSAGE", width=300),
                    "created":       st.column_config.TextColumn("CREATED", width=130),
                })
        else:
            empty_chart("No tickets match the selected filters")
    sp(32)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer">'
    '<div class="footer-copy">CRYPTOOPS  ·  INTERNAL USE ONLY  ·  v1.0.0</div>'
    '<div class="footer-credit">Built by '
    '<a href="https://www.linkedin.com/in/bilal-etudaiye-muhtar-2725a317a'
    '?utm_source=share&amp;utm_campaign=share_via&amp;utm_content=profile&amp;utm_medium=ios_app"'
    ' target="_blank">Bilal Etudaiye-Muhtar</a>'
    '</div></div>',
    unsafe_allow_html=True,
)
