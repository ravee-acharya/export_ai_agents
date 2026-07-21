import streamlit as st

from services.export_service import ExportService
from ui.sidebar import render_sidebar
try:
    from ui.theme import apply_theme
except Exception:
    apply_theme = lambda: None
from ui.chat import (
    render_chat_history,
    add_user_message,
    add_assistant_message,
)
from ui.dashboard import render_dashboard, render_token_badge
from ui.layout import create_layout

st.set_page_config(
    page_title="ExportAI",
    page_icon="🌍",
    layout="wide",
)

apply_theme()
st.title("🌍 ExportAI")
st.caption("AI-powered Export Intelligence Assistant")

provider, debug, certifications = render_sidebar()

left_panel, chat_panel, right_panel = create_layout()

if "export_service" not in st.session_state:
    st.session_state.export_service = ExportService(provider)

service = st.session_state.export_service

if service.provider != provider:
    service.provider = provider
    service.graph = None

with chat_panel:
    render_chat_history()

with chat_panel:
    question = st.chat_input("Ask about export opportunities...")

if question:
    add_user_message(question)

    with chat_panel:
        with st.chat_message("user"):
            st.markdown(question)

    result = None
    answer = None

    with chat_panel:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing export opportunities..."):
                try:
                    result = service.analyze_query(
                        question,
                        certifications=certifications,
                    )
                    answer = result.get("summary", "No summary generated.")
                    st.markdown(answer)
                except Exception as ex:
                    answer = str(ex)
                    st.error(answer)

    add_assistant_message(answer)

    if result:
        with right_panel:
            if debug:
                st.subheader("Developer Output")
                st.json(result)
            render_dashboard(result)
        render_token_badge(result)
