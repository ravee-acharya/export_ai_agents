import streamlit as st

st.set_page_config(page_title="ExportAI", page_icon="🌍", layout="wide")
st.title("🌍 ExportAI")
st.write("App is loading...")

try:
    from ui.sidebar import render_sidebar
    provider, debug, certifications = render_sidebar()
    st.success(f"Sidebar OK — provider: {provider}")
except Exception as e:
    st.error(f"Sidebar failed: {e}")

try:
    from ui.layout import create_layout
    left, chat, right = create_layout()
    st.success("Layout OK")
except Exception as e:
    st.error(f"Layout failed: {e}")

try:
    from ui.dashboard import render_dashboard, render_token_badge
    st.success("Dashboard import OK")
except Exception as e:
    st.error(f"Dashboard import failed: {e}")

try:
    from services.export_service import ExportService
    st.success("ExportService import OK")
except Exception as e:
    st.error(f"ExportService failed: {e}")

st.write("All imports done.")
