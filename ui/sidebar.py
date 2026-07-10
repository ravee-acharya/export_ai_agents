import streamlit as st


def render_sidebar():

    with st.sidebar:

        st.header("⚙️ Settings")

        provider = st.selectbox(
            "LLM Provider",
            [
                "gemini",
                "anthropic",
                "ollama",
                "openrouter",
            ],
            index=0,
        )

        debug = st.checkbox(
            "Developer Mode",
            value=False,
        )

    return provider, debug