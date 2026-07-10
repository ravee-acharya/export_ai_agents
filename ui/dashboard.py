import streamlit as st


def render_dashboard(result):

    if not result:
        return

    # ---------------------------------
    # Summary
    # ---------------------------------

    summary = result.get("summary")

    if summary:
        st.markdown(summary)

    # ---------------------------------
    # Opportunity Scores
    # ---------------------------------

    scores = result.get("opportunity_scores", [])

    if scores:

        st.divider()
        st.subheader("📊 Opportunity Scores")

        for score in scores:

            col1, col2 = st.columns([4, 1])

            with col1:

                st.markdown(
                    f"""
**HS Code:** {score['hs_code']}

**Country:** {score['destination_country']}
"""
                )

            with col2:

                st.metric(
                    "Score",
                    f"{score['score']:.1f}",
                )

    # ---------------------------------
    # Government Schemes
    # ---------------------------------

    scheme_output = result.get("scheme_compliance_output")

    if scheme_output:

        schemes = scheme_output.eligible_schemes()

        if schemes:

            st.divider()
            st.subheader("🏛 Government Schemes")

            for scheme in schemes:

                with st.expander(scheme.name):

                    st.write(
                        f"**Issued By:** {scheme.issuing_body}"
                    )

                    st.write(
                        scheme.benefit_summary
                    )