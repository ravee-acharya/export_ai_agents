"""
ExportAI visual theme — Material Design 3 tokens from the approved
"ExportAI Intelligence Platform" design.

Fonts: Hanken Grotesk (headlines), Inter (body), JetBrains Mono (labels)
Colors: MD3 semantic tokens (primary/secondary/surface/error families)
"""

import streamlit as st


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=block');

:root {
    --bg:            #f7f9fb;
    --on-bg:         #191c1e;
    --surface-low:   #f2f4f6;
    --surface:       #eceef0;
    --surface-high:  #e6e8ea;
    --surface-highest: #e0e3e5;
    --surface-lowest: #ffffff;
    --outline:       #76777d;
    --outline-var:   #c6c6cd;
    --primary:       #000000;
    --primary-container: #131b2e;
    --on-primary:    #ffffff;
    --on-primary-container: #7c839b;
    --secondary:     #006c49;
    --secondary-container: #6cf8bb;
    --secondary-fixed-dim: #4edea3;
    --on-secondary:  #ffffff;
    --on-secondary-container: #00714d;
    --error:         #ba1a1a;
    --error-container: #ffdad6;
    --on-error-container: #93000a;
}

html, body {
    font-family: 'Inter', sans-serif;
}

[data-testid="stIconMaterial"],
[data-testid*="Icon"] {
    font-family: 'Material Symbols Outlined' !important;
}

.stApp { background: var(--bg) !important; }

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--surface-low) !important;
    border-right: 1px solid var(--outline-var) !important;
}
[data-testid="stSidebar"] * { color: var(--on-bg) !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
    color: var(--outline) !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-weight: 800 !important;
    color: var(--on-bg) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--surface-lowest) !important;
    border-color: var(--outline-var) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * { color: var(--on-bg) !important; }

/* ── Main content ─────────────────────────────────────── */
.main .block-container { padding-top: 1.5rem !important; max-width: 100% !important; }

h1, h2, h3 {
    font-family: 'Hanken Grotesk', sans-serif !important;
    color: var(--on-bg) !important;
    letter-spacing: -0.01em !important;
}
h1 { font-weight: 700 !important; font-size: 1.6rem !important; }
h2 { font-weight: 600 !important; font-size: 1.15rem !important; }
h3 { font-weight: 600 !important; font-size: 1rem !important; }

[data-testid="stMarkdownContainer"] > p,
[data-testid="stMarkdownContainer"] > ul li,
[data-testid="stMarkdownContainer"] > ol li {
    color: var(--on-bg);
    font-family: 'Inter', sans-serif;
}

/* ── Metrics ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--surface-lowest) !important;
    border: 1px solid var(--outline-var) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--outline) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: .05em !important;
}
[data-testid="stMetricValue"] {
    color: var(--on-bg) !important;
    font-family: 'Hanken Grotesk', sans-serif !important;
    font-size: 22px !important;
    font-weight: 700 !important;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
    background: var(--primary) !important;
    color: var(--on-primary) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 18px !important;
}
.stButton > button:hover { opacity: .9 !important; }

.stDownloadButton > button {
    background: var(--secondary-container) !important;
    color: var(--on-secondary-container) !important;
    border: 1px solid var(--secondary) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}

/* ── Chat ─────────────────────────────────────────────── */
[data-testid="stChatInput"] { border-top: 1px solid var(--outline-var) !important; background: var(--surface-lowest) !important; }
[data-testid="stChatInput"] textarea {
    background: var(--surface-low) !important;
    border: 1px solid var(--outline-var) !important;
    border-radius: 24px !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--on-bg) !important;
    font-size: 13px !important;
}
[data-testid="stChatInput"] button { background: var(--primary) !important; border-radius: 20px !important; }

[data-testid="stChatMessage"] {
    background: var(--surface-lowest) !important;
    border: 1px solid var(--outline-var) !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
    margin-bottom: 8px !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: var(--primary-container) !important;
    border-color: var(--primary-container) !important;
    color: #fff !important;
}

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid var(--outline-var) !important; gap: 2px !important; }
[data-testid="stTabs"] [role="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: var(--outline) !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 9px 16px !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--on-secondary-container) !important;
    background: var(--secondary-container) !important;
    border-bottom: 2px solid var(--secondary) !important;
}

/* ── Expander ─────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--surface-lowest) !important;
    border: 1px solid var(--outline-var) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: var(--on-bg) !important;
    font-size: 13.5px !important;
}

/* ── Inputs ───────────────────────────────────────────── */
[data-baseweb="select"] > div {
    background: var(--surface-lowest) !important;
    border-color: var(--outline-var) !important;
    border-radius: 8px !important;
    color: var(--on-bg) !important;
}
[data-testid="stTextInput"] input {
    background: var(--surface-lowest) !important;
    border-color: var(--outline-var) !important;
    border-radius: 8px !important;
    color: var(--on-bg) !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stCheckbox"] label {
    font-size: 13px !important; font-weight: 500 !important; color: var(--outline) !important;
}

/* ── Alerts ───────────────────────────────────────────── */
.stSuccess { background: var(--secondary-container) !important; border-left: 4px solid var(--secondary) !important; color: var(--on-secondary-container) !important; border-radius: 8px !important; }
.stWarning { background: #fdf0dc !important; border-left: 4px solid #d68a2b !important; color: #7a4a0e !important; border-radius: 8px !important; }
.stError   { background: var(--error-container) !important; border-left: 4px solid var(--error) !important; color: var(--on-error-container) !important; border-radius: 8px !important; }
.stInfo    { background: #eaf1f4 !important; border-left: 4px solid var(--secondary) !important; color: #0b4a42 !important; border-radius: 8px !important; }

/* ── Misc ─────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--outline-var); border-radius: 5px; }
::-webkit-scrollbar-track { background: transparent; }
hr { border-color: var(--outline-var) !important; margin: 16px 0 !important; }
.stCaption, small, [data-testid="stCaptionContainer"] {
    color: var(--outline) !important; font-size: 11.5px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stSpinner > div { border-top-color: var(--secondary) !important; }
header[data-testid="stHeader"] { background: var(--surface-lowest) !important; border-bottom: 1px solid var(--outline-var) !important; }
"""


def apply_theme() -> None:
    """Inject the ExportAI Intelligence Platform Material Design theme."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_score_ring(score: float, label: str = "Score") -> str:
    """SVG ring chart matching the design's score visualization."""
    tier_color = (
        "#006c49" if score >= 60 else
        "#d68a2b" if score >= 30 else
        "#ba1a1a"
    )
    r = 28
    c = 2 * 3.14159 * r
    dash = f"{score / 100 * c:.1f} {c:.1f}"
    return f"""
<div style="position:relative;width:72px;height:72px;display:inline-block;">
  <svg width="72" height="72" viewBox="0 0 72 72">
    <circle cx="36" cy="36" r="{r}" fill="none" stroke="#e0e3e5" stroke-width="7"/>
    <circle cx="36" cy="36" r="{r}" fill="none" stroke="{tier_color}"
            stroke-width="7" stroke-linecap="round"
            stroke-dasharray="{dash}" transform="rotate(-90 36 36)"/>
  </svg>
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;
              align-items:center;justify-content:center;">
    <span style="font-size:15px;font-weight:700;color:#191c1e;
                 font-family:'Hanken Grotesk',sans-serif;">{score:.0f}</span>
    <span style="font-size:9px;color:#76777d;font-family:'JetBrains Mono',monospace;">{label}</span>
  </div>
</div>"""
