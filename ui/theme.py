"""
ExportAI visual theme.

One place for the app's entire look: a maritime-trade palette (deep
harbor navy, brass, teal), glass-panel cards, and depth cues (layered
shadows, subtle borders, hover lift). Injected once from app.py via
apply_theme(); no other module needs to know CSS exists.

Streamlit constraint worth knowing: Streamlit renders its own DOM and
only exposes styling through injected CSS targeting its generated
class names / data-testids. Those identifiers are stable across minor
versions but CAN change on major Streamlit upgrades -- if styling
breaks after an upgrade, this file is the only place to fix.
"""

import streamlit as st

_THEME_CSS = """
<style>
/* ============ PALETTE ============
   harbor navy  #0D1220  (app background)
   panel navy   #161D33  (cards)
   brass        #E3A857  (primary accent -- headers, highlights)
   teal         #3FB8AF  (live data, positive)
   coral        #E2725B  (risk, warnings)
   parchment    #EDEAE2  (primary text)
   mist         #9CA3BF  (secondary text)
*/

/* ---------- App shell ---------- */
body {
    background: #0D1220 !important;
}
.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 10% 0%, rgba(63,184,175,0.05), transparent),
        radial-gradient(ellipse 60% 40% at 95% 100%, rgba(227,168,87,0.04), transparent),
        rgba(13,18,32,0.72);
    color: #EDEAE2;
    /* No z-index here — setting it would create a stacking context
       that buries Streamlit's own fixed-position chat input bar */
    position: relative;
}
[data-testid="stHeader"] {
    background: transparent !important;
}
[data-testid="stBottom"] {
    background: rgba(13,18,32,0.85) !important;
    backdrop-filter: blur(8px);
    z-index: 9999 !important;
}

/* ---------- Typography ---------- */
h1, h2, h3 {
    font-family: Georgia, 'Times New Roman', serif !important;
    color: #F6F3EC !important;
    letter-spacing: 0.2px;
}
h1 span.brand-accent { color: #E3A857; }

.stMarkdown, .stMarkdown p, .stCaption, [data-testid="stCaptionContainer"] {
    color: #C9C6BC;
}

/* ---------- Glass cards: expanders ---------- */
[data-testid="stExpander"] {
    background: rgba(22,29,51,0.82);
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(6px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    margin-bottom: 10px;
}
[data-testid="stExpander"]:hover {
    transform: translateY(-2px);
    border-color: rgba(227,168,87,0.45) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(227,168,87,0.2);
}
[data-testid="stExpander"] summary {
    color: #EDEAE2 !important;
    font-weight: 600;
}

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 3px 14px rgba(0,0,0,0.3);
}
[data-testid="stMetricValue"] {
    color: #E3A857 !important;
    font-family: Georgia, serif !important;
}
[data-testid="stMetricLabel"] {
    color: #9CA3BF !important;
}

/* ---------- Chat ---------- */
[data-testid="stChatMessage"] {
    background: rgba(22,29,51,0.85);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    box-shadow: 0 3px 16px rgba(0,0,0,0.3);
    backdrop-filter: blur(5px);
}
[data-testid="stChatInput"] textarea {
    background: #161D33 !important;
    color: #EDEAE2 !important;
    border-radius: 12px !important;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10172B 0%, #0D1220 100%);
    border-right: 1px solid rgba(255,255,255,0.07);
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #E3A857 !important;
}

/* ---------- Buttons & inputs ---------- */
.stButton button, .stDownloadButton button {
    background: linear-gradient(140deg, #E3A857, #C98D3E);
    color: #14192C;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(227,168,87,0.3);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(227,168,87,0.45);
}
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div,
.stTextInput input {
    background: #161D33 !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #EDEAE2 !important;
    border-radius: 10px !important;
}

/* ---------- Alert banners (risk levels etc.) ---------- */
[data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(4px);
}

/* ---------- Dividers ---------- */
hr {
    border-color: rgba(255,255,255,0.08) !important;
}

/* ---------- Score ring (used in dashboard) ---------- */
.score-ring-3d {
    position: relative;
    width: 110px;
    height: 110px;
    margin: 6px auto;
}
.score-ring-3d svg { transform: rotate(-90deg); }
.score-ring-3d .ring-bg { stroke: rgba(255,255,255,0.09); }
.score-ring-3d .ring-fg {
    stroke: url(#scoreGradient);
    stroke-linecap: round;
    filter: drop-shadow(0 0 6px rgba(63,184,175,0.55));
    transition: stroke-dashoffset 1s ease;
}
.score-ring-3d .ring-value {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: Georgia, serif;
    font-size: 26px;
    font-weight: 700;
    color: #F6F3EC;
}
.score-ring-3d .ring-value small {
    font-size: 10px;
    color: #9CA3BF;
    font-family: Arial, sans-serif;
    font-weight: 400;
}

/* Respect reduced-motion preferences */
@media (prefers-reduced-motion: reduce) {
    [data-testid="stExpander"], .stButton button { transition: none; }
}
</style>
"""


def apply_theme() -> None:
    """Inject the global theme CSS. Call once, early, from app.py."""
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def render_score_ring(score: float, label: str = "Score") -> str:
    """
    Return HTML for an animated circular score ring (0-100). Rendered
    via st.markdown(..., unsafe_allow_html=True) by the dashboard.
    """
    score = max(0.0, min(100.0, float(score)))
    circumference = 2 * 3.14159 * 46
    offset = circumference * (1 - score / 100)

    return f"""
    <div class="score-ring-3d">
      <svg width="110" height="110" viewBox="0 0 110 110">
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#E3A857"/>
            <stop offset="100%" stop-color="#3FB8AF"/>
          </linearGradient>
        </defs>
        <circle class="ring-bg" cx="55" cy="55" r="46" fill="none" stroke-width="9"/>
        <circle class="ring-fg" cx="55" cy="55" r="46" fill="none" stroke-width="9"
                stroke-dasharray="{circumference:.1f}"
                stroke-dashoffset="{offset:.1f}"/>
      </svg>
      <div class="ring-value">{score:.0f}<small>{label}</small></div>
    </div>
    """
