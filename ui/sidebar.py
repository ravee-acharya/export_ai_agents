import streamlit as st

COMMON_CERTIFICATIONS = [
    "ISO 9001",
    "ISO 14001",
    "OEKO-TEX Standard 100",
    "BSCI Social Compliance",
    "Udyam Registration",
    "GOTS (Global Organic Textile Standard)",
]


def render_sidebar():

    with st.sidebar:

        st.header("⚙️ Settings")

        provider = st.selectbox(
            "LLM Provider",
            ["groq", "gemini", "anthropic", "openrouter", "ollama"],
            index=0,
            key="llm_provider",          # explicit key prevents state conflicts on reboot
        )

        debug = st.checkbox(
            "Developer Mode",
            value=False,
            key="developer_mode",
        )

        st.divider()
        st.subheader("🏭 Your SME Profile")
        st.caption(
            "Used by the Capability Gap Agent to assess certification "
            "readiness for your target markets."
        )

        selected = st.multiselect(
            "Certifications you currently hold",
            options=COMMON_CERTIFICATIONS,
            key="certifications_selected",
        )

        other = st.text_input(
            "Other certifications (comma-separated)",
            placeholder="e.g. FSC Chain of Custody, WRAP",
            key="certifications_other",
        )

        other_list = [c.strip() for c in other.split(",") if c.strip()]
        certifications = list(dict.fromkeys(selected + other_list))

    return provider, debug, certifications
