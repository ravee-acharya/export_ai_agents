import streamlit as st

# Explicit emoji avatars -- Streamlit's default chat avatar relies on
# its own internal icon system, which was rendering the icon name as
# literal text ("smart_toy") instead of an icon on this deployment.
# Plain emoji always render correctly since they're just Unicode
# characters, not dependent on any icon font loading.
_AVATARS = {"user": "🧑\u200d💼", "assistant": "🤖"}


def clean_llm_text(text: str) -> str:
    """
    Strip stray single backticks from LLM-generated text before
    rendering with st.markdown().

    LLMs frequently wrap numbers/prices in backticks (e.g. `6.59`)
    out of habit from code-generation training, with no code-block
    intent. Markdown renders single backticks as inline `<code>`,
    which browsers display in a monospace font with a gray
    background -- causing the same paragraph to visually mix two
    different fonts mid-sentence. Since a natural-language summary
    never legitimately needs inline code formatting, backticks are
    safe to strip outright rather than trying to distinguish
    intentional from accidental usage.
    """
    if not text:
        return text
    return text.replace("`", "")


def render_chat_history():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Show newest message first
    for message in reversed(st.session_state.messages):
        avatar = _AVATARS.get(message["role"])
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(clean_llm_text(message["content"]))


def add_user_message(message):
    st.session_state.messages.append({"role": "user", "content": message})


def add_assistant_message(message):
    st.session_state.messages.append({"role": "assistant", "content": message})
