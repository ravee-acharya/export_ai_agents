import streamlit as st


def render_chat_history():

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def add_user_message(message):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": message,
        }
    )


def add_assistant_message(message):

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": message,
        }
    )