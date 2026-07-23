import streamlit as st

st.set_page_config(
    page_title="ExportAI",
    page_icon="🌍",
    layout="wide",
)

try:
    from ui.theme import apply_theme
    apply_theme()
except Exception:
    pass

from ui.sidebar import render_sidebar
from ui.chat import render_chat_history, add_user_message, add_assistant_message, clean_llm_text
from ui.dashboard import render_dashboard, render_token_badge, render_export_buttons
from ui.layout import create_layout
from services.export_service import ExportService

# ── Title row with Export buttons top-right ─────────────────────
# (The "Share / Manage app" bar above this is Streamlit Cloud's own
# platform toolbar -- outside our app entirely, no API to inject
# into it. This row is the top-right of OUR app's own content area.)
title_col, export_col = st.columns([3, 1])

with title_col:
    st.title("🌍 ExportAI")
    st.caption("AI-powered Export Intelligence Assistant")

with export_col:
    if st.session_state.get("last_result"):
        render_export_buttons(st.session_state["last_result"])

provider, debug, certifications = render_sidebar()
chat_panel, right_panel = create_layout()

if "export_service" not in st.session_state:
    st.session_state.export_service = ExportService(provider)

service = st.session_state.export_service

if service.provider != provider:
    service.provider = provider
    service.graph = None

with chat_panel:
    question = st.chat_input("Ask about export opportunities...")

with chat_panel:
    render_chat_history()

if question:
    add_user_message(question)

    with chat_panel:
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(question)

    result = None
    answer = None

    with chat_panel:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing export opportunities..."):
                try:
                    result = service.analyze_query(
                        question,
                        certifications=certifications,
                    )
                    answer = result.get("summary", "No summary generated.")
                    st.markdown(clean_llm_text(answer))
                except Exception as ex:
                    answer = str(ex)
                    st.error(answer)

    add_assistant_message(answer)

    if result:
        st.session_state["last_result"] = result

# ── Dashboard renders from persisted state, on EVERY rerun --
# not gated behind a fresh question. Widgets inside the dashboard
# (the Analytical/Intelligence toggle, tabs, export buttons) each
# trigger their own script rerun where `question` is None again --
# gating dashboard render behind `if question:` made those widgets
# blank the whole right panel the instant they were touched.
if st.session_state.get("last_result"):
    result = st.session_state["last_result"]
    with right_panel:
        if debug:
            st.subheader("Developer Output")
            st.json(result)
        try:
            render_dashboard(result)
        except Exception as e:
            st.error(f"Dashboard error: {e}")
    try:
        render_token_badge(result)
    except Exception:
        pass
