import streamlit as st

from services.export_service import ExportService
from ui.sidebar import render_sidebar
from ui.chat import (
    render_chat_history,
    add_user_message,
    add_assistant_message,
)
from ui.dashboard import render_dashboard
from ui.layout import create_layout


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="ExportAI",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 ExportAI")
st.caption("AI-powered Export Intelligence Assistant")


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

provider, debug = render_sidebar()


# --------------------------------------------------
# Layout
# --------------------------------------------------

left_panel, chat_panel, right_panel = create_layout()


# --------------------------------------------------
# Service
# --------------------------------------------------

service = ExportService(provider)


# --------------------------------------------------
# Chat History
# --------------------------------------------------

with chat_panel:
    render_chat_history()


# --------------------------------------------------
# Chat Input
# --------------------------------------------------

with chat_panel:
    question = st.chat_input(
        "Ask about export opportunities..."
    )


# --------------------------------------------------
# Process User Question
# --------------------------------------------------

if question:

    # Store user message
    add_user_message(question)

    # Show user message
    with chat_panel:
        with st.chat_message("user"):
            st.markdown(question)

    result = None

    # Generate response
    with chat_panel:
        with st.chat_message("assistant"):

            with st.spinner("Analyzing export opportunities..."):

                try:

                    # --------------------------------------------------
                    # TEMPORARY
                    # We will switch back to analyze_query()
                    # after fixing the Parse Query Agent.
                    # --------------------------------------------------

                    result = service.analyze_query(question)

                    answer = result.get(
                        "summary",
                        "No summary generated."
                    )

                    st.markdown(answer)

                except Exception as ex:

                    answer = str(ex)

                    st.error(answer)

    # Save assistant message
    add_assistant_message(answer)

    # --------------------------------------------------
    # Right Panel
    # --------------------------------------------------

    if result:

        with right_panel:

            if debug:
                st.subheader("Developer Output")
                st.json(result)

            render_dashboard(result)