import streamlit as st

# Explicit emoji avatars -- Streamlit's default chat avatar relies on
# its own internal icon system, which was rendering the icon name as
# literal text ("smart_toy") instead of an icon on this deployment.
# Plain emoji always render correctly since they're just Unicode
# characters, not dependent on any icon font loading.
_AVATARS = {"user": "🧑\u200d💼", "assistant": "🤖"}


def render_chat_history():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Show newest message first
    for message in reversed(st.session_state.messages):
        avatar = _AVATARS.get(message["role"])
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])


def add_user_message(message):
    st.session_state.messages.append({"role": "user", "content": message})


def add_assistant_message(message):
    st.session_state.messages.append({"role": "assistant", "content": message})
