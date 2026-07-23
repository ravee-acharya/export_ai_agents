import streamlit as st


def create_layout():
    """
    Two-column layout: dashboard 60%, chat 40%.
    (Previously three columns with an unused left column that just
    ate 25% of the page width as permanent blank space -- removed.)
    """
    dashboard, chat = st.columns([3, 2], gap="large")
    return chat, dashboard
