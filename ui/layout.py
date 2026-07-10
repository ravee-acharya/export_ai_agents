import streamlit as st


def create_layout():

    left, center, right = st.columns(
        [1, 2, 1],
        gap="large",
    )

    return left, center, right