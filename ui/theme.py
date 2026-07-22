"""
ExportAI visual theme — implements the Export Trading Terminal design.

Design tokens from the approved design:
  bg        #f4f1ea  warm cream background
  card      #ffffff  white cards
  ink       #221f1a  near-black text
  sub       #6d675c  secondary text
  faint     #a29b8c  tertiary / placeholders
  line      #e7e0d3  borders and dividers
  brand     #0e7a6b  teal brand primary
  brandsoft #e3f1ee  teal background tint
  go        #2f9e6e  positive / green
  warn      #d68a2b  amber / moderate
  weak      #d15b4a  red / negative

Font: Plus Jakarta Sans (Google Fonts, loaded via @import)
"""

import streamlit as st


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

:root {
    --bg:        #f4f1ea;
    --card:      #ffffff;
    --ink:       #221f1a;
    --sub:       #6d675c;
    --faint:     #a29b8c;
    --line:      #e7e0d3;
    --brand:     #0e7a6b;
    --brandsoft: #e3f1ee;
    --go:        #2f9e6e;
    --warn:      #d68a2b;
    --weak:      #d15b4a;
    --sky:       #eaf1f4;
}

/* ── Base ─────────────────────────────────────────────── */
/* Scoped to html/body only -- NEVER a blanket [class*="css"]
   selector. Streamlit renders icons (chat avatars, button chevrons,
   expander arrows) via font ligatures: the text "smart_toy" or
   "arrow_right" IS the icon, rendered as a glyph by a specific icon
   font. A blanket font-family override on every div/span breaks
   that ligature and prints the raw icon name as literal text
   instead of the icon -- this is what was happening before. */
html, body {
    font-family: 'Plus Jakarta Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* Protect Streamlit's icon font from any font-family override below */
[data-testid="stIconMaterial"],
[data-testid*="Icon"],
.material-icons,
.material-icons-outlined {
    font-family: 'Material Symbols Outlined', 'Material Icons' !important;
}

.stApp {
    background: var(--bg) !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--card) !important;
    border-right: 1px solid var(--line) !important;
}

[data-testid="stSidebar"] * {
    color: var(--ink) !important;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {
    color: var(--sub) !important;
    font-size: 13px !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--ink) !important;
    font-weight: 800 !important;
}

/* Sidebar selectbox + multiselect -- explicit text color at every
   nesting level. Works together with .streamlit/config.toml's
   base="light" theme rather than fighting Streamlit's dark-mode
   auto-detection underneath it. */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--card) !important;
    border-color: var(--line) !important;
    border-radius: 10px !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: var(--ink) !important;
}

/* ── Main content ─────────────────────────────────────── */
.main .block-container {
    padding-top: 1.5rem !important;
    max-width: 100% !important;
}

h1, h2, h3 {
    color: var(--ink) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    letter-spacing: -0.01em !important;
}

h1 { font-weight: 800 !important; font-size: 1.6rem !important; }
h2 { font-weight: 800 !important; font-size: 1.15rem !important; }
h3 { font-weight: 700 !important; font-size: 1rem !important; }

/* Text color ONLY for genuine Streamlit-rendered markdown/text --
   NEVER a bare div/span rule. Our custom HTML cards (hero banner,
   score cards, buyer cards) set their own explicit inline colors
   for a reason (white text on a dark teal background, etc). A rule
   here that touches raw <div>/<span> forces every child element's
   color via direct assignment, which beats inherited color from a
   parent's inline style regardless of specificity -- that's what
   was making the dark teal hero banner's text render as near-black
   ink instead of the white it was set to. */
[data-testid="stMarkdownContainer"] > p,
[data-testid="stMarkdownContainer"] > ul li,
[data-testid="stMarkdownContainer"] > ol li {
    color: var(--ink);
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── Cards (st.container with border) ────────────────── */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div {
    background: var(--card);
}

/* ── Metrics ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--card) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
}

[data-testid="stMetricLabel"] {
    color: var(--sub) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}

[data-testid="stMetricValue"] {
    color: var(--ink) !important;
    font-size: 22px !important;
    font-weight: 800 !important;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
    background: var(--brand) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    padding: 10px 18px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: background 0.15s ease !important;
}

.stButton > button:hover {
    background: #0b6558 !important;
}

/* Download button */
.stDownloadButton > button {
    background: var(--brandsoft) !important;
    color: var(--brand) !important;
    border: 1px solid var(--brand) !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}

/* ── Chat ─────────────────────────────────────────────── */
[data-testid="stChatInput"] {
    border-top: 1px solid var(--line) !important;
    background: var(--card) !important;
}

[data-testid="stChatInput"] textarea {
    background: var(--bg) !important;
    border: 1px solid var(--line) !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--ink) !important;
    font-size: 13px !important;
}

[data-testid="stChatInput"] button {
    background: var(--brand) !important;
    border-radius: 10px !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: var(--card) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
    margin-bottom: 8px !important;
}

/* User message */
[data-testid="stChatMessage"][data-testid*="user"] {
    background: var(--brand) !important;
    border-color: var(--brand) !important;
    color: #fff !important;
}

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid var(--line) !important;
    gap: 2px !important;
}

[data-testid="stTabs"] [role="tab"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: var(--sub) !important;
    border-radius: 9px 9px 0 0 !important;
    padding: 9px 16px !important;
    border: none !important;
    background: transparent !important;
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--brand) !important;
    background: var(--brandsoft) !important;
    border-bottom: 2px solid var(--brand) !important;
}

/* ── Expander ─────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--card) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
}

[data-testid="stExpander"] summary {
    font-weight: 700 !important;
    color: var(--ink) !important;
    font-size: 13.5px !important;
}

/* ── Selectbox ────────────────────────────────────────── */
[data-baseweb="select"] > div {
    background: var(--card) !important;
    border-color: var(--line) !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    color: var(--ink) !important;
}

/* ── Text input ───────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: var(--card) !important;
    border-color: var(--line) !important;
    border-radius: 10px !important;
    color: var(--ink) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
}

/* ── Checkbox ─────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--sub) !important;
}

/* ── Alerts / banners ─────────────────────────────────── */
.stSuccess {
    background: #e8f5ee !important;
    border-left: 4px solid var(--go) !important;
    color: #1a5c3a !important;
    border-radius: 10px !important;
}

.stWarning {
    background: #fdf0dc !important;
    border-left: 4px solid var(--warn) !important;
    color: #7a4a0e !important;
    border-radius: 10px !important;
}

.stError {
    background: #fce8e4 !important;
    border-left: 4px solid var(--weak) !important;
    color: #7a2018 !important;
    border-radius: 10px !important;
}

.stInfo {
    background: var(--sky) !important;
    border-left: 4px solid var(--brand) !important;
    color: #0b4a42 !important;
    border-radius: 10px !important;
}

/* ── Scrollbar ────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb {
    background: var(--line);
    border-radius: 5px;
}
::-webkit-scrollbar-track { background: transparent; }

/* ── Plotly charts ────────────────────────────────────── */
/* Override dark chart backgrounds to match light theme */
.js-plotly-plot .plotly .bg { fill: transparent !important; }

/* ── Divider ──────────────────────────────────────────── */
hr {
    border-color: var(--line) !important;
    margin: 16px 0 !important;
}

/* ── Caption / small text ─────────────────────────────── */
.stCaption, small, [data-testid="stCaptionContainer"] {
    color: var(--faint) !important;
    font-size: 11.5px !important;
}

/* ── Spinner ──────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: var(--brand) !important;
}

/* ── Page title bar ───────────────────────────────────── */
header[data-testid="stHeader"] {
    background: var(--card) !important;
    border-bottom: 1px solid var(--line) !important;
}
"""


def apply_theme() -> None:
    """Inject the Export Trading Terminal design system into the Streamlit app."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_score_ring(score: float, label: str = "Score") -> str:
    """Return an SVG ring chart as an HTML string."""
    _tier_color = (
        "#2f9e6e" if score >= 60 else
        "#d68a2b" if score >= 30 else
        "#d15b4a"
    )
    r = 28
    c = 2 * 3.14159 * r
    dash = f"{score / 100 * c:.1f} {c:.1f}"
    return f"""
<div style="position:relative;width:72px;height:72px;display:inline-block;">
  <svg width="72" height="72" viewBox="0 0 72 72">
    <circle cx="36" cy="36" r="{r}" fill="none" stroke="#e7e0d3" stroke-width="7"/>
    <circle cx="36" cy="36" r="{r}" fill="none" stroke="{_tier_color}"
            stroke-width="7" stroke-linecap="round"
            stroke-dasharray="{dash}" transform="rotate(-90 36 36)"/>
  </svg>
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;
              align-items:center;justify-content:center;">
    <span style="font-size:15px;font-weight:800;color:#221f1a;
                 font-family:'Plus Jakarta Sans',sans-serif;">{score:.0f}</span>
    <span style="font-size:9px;color:#a29b8c;">{label}</span>
  </div>
</div>"""
