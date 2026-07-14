import streamlit as st

from ui.trade_globe import render_trade_globe
from ui.theme import render_score_ring


_RISK_LEVEL_STYLE = {
    "Low": ("🟢", st.success),
    "Moderate": ("🟡", st.warning),
    "High": ("🟠", st.warning),
    "Severe": ("🔴", st.error),
}


def render_dashboard(result):

    if not result:
        return

    _render_summary(result)
    _render_trade_globe_section(result)
    _render_opportunity_scores(result)
    _render_pricing(result)
    _render_capability_gap(result)
    _render_logistics(result)
    _render_risk(result)
    _render_competitors(result)
    _render_buyer_discovery(result)
    _render_fta(result)
    _render_document_intelligence(result)
    _render_certification(result)
    _render_schemes(result)
    _render_rag(result)
    _render_errors(result)


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

def _render_summary(result):
    summary = result.get("summary")
    if summary:
        st.markdown(summary)


# ------------------------------------------------------------------
# Trade Routes Globe (signature visual)
# ------------------------------------------------------------------

def _render_trade_globe_section(result):
    scores = result.get("opportunity_scores", [])
    if not scores:
        return

    st.divider()
    st.subheader("🌍 Your Trade Routes")
    st.caption(
        "Arcs fly from India to each target market — color shows opportunity "
        "strength, marker size shows score. Drag to rotate, scroll to zoom."
    )
    render_trade_globe(scores)


# ------------------------------------------------------------------
# Opportunity Scores
# ------------------------------------------------------------------

def _render_opportunity_scores(result):
    scores = result.get("opportunity_scores", [])

    if not scores:
        return

    st.divider()
    st.subheader("📊 Opportunity Scores")

    for score in scores:

        breakdown = score.get("score_breakdown", {})

        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(
                f"**HS Code:** {score['hs_code']}  \n"
                f"**Country:** {score['destination_country']}"
            )

        with col2:
            st.markdown(
                render_score_ring(score["score"], "Score"),
                unsafe_allow_html=True,
            )

        with st.expander("Show scoring factors"):

            factor_cols = st.columns(3)

            with factor_cols[0]:
                st.caption("Demand & Competition")
                st.write(f"Growth: {breakdown.get('demand_growth_pct', '—')}%")
                st.write(f"Surge detected: {breakdown.get('surge_detected', '—')}")
                st.write(f"Competition density: {breakdown.get('competition_density', '—')}")
                st.write(f"Active Indian suppliers: {breakdown.get('active_indian_suppliers', '—')}")

            with factor_cols[1]:
                st.caption("Pricing")
                if "recommended_fob_price" in breakdown:
                    st.write(f"FOB price: ${breakdown['recommended_fob_price']}")
                    st.write(f"Margin: {breakdown['expected_margin_pct']}%")
                    st.write(f"Competitiveness: {breakdown['competitiveness_score']}/10")
                else:
                    st.write("No pricing data for this pair")
                st.write(f"Import gap: {breakdown.get('import_gap', '—')}")
                st.write(f"Price premium: {breakdown.get('price_premium', '—')}")

            with factor_cols[2]:
                st.caption("Capability & Logistics")
                st.write(f"Capability distance: {breakdown.get('capability_distance', '—')}")
                if "capability_gap_score" in breakdown:
                    st.write(f"Gap score: {breakdown['capability_gap_score']}/5")
                st.write(f"Logistics cost: {breakdown.get('logistics_cost', '—')}")
                if "sea_transit_days" in breakdown:
                    st.write(f"Transit: {breakdown['sea_transit_days']} days")

            if breakdown.get("missing_requirements"):
                st.caption("Missing certifications for this market:")
                st.write(", ".join(breakdown["missing_requirements"]))

            note = score.get("note")
            if note:
                st.caption(note)

        st.markdown("")


# ------------------------------------------------------------------
# Pricing Signals
# ------------------------------------------------------------------

def _render_pricing(result):
    pricing_output = result.get("pricing_output")

    if not pricing_output or not pricing_output.pricing:
        return

    st.divider()
    st.subheader("💰 Pricing Intelligence")

    for p in pricing_output.pricing:

        with st.expander(f"{p.hs_code} → {p.destination_country}"):

            cols = st.columns(4)
            cols[0].metric("Recommended FOB", f"${p.recommended_fob_price}")
            cols[1].metric("Expected Margin", f"{p.expected_margin_pct}%")
            cols[2].metric("Competitiveness", f"{p.competitiveness_score}/10")
            cols[3].metric("Est. Retail Price", f"${p.estimated_retail_price}")

            st.caption(
                f"Avg import price: ${p.average_import_price} · "
                f"Avg Indian export price: ${p.average_indian_export_price}"
            )


# ------------------------------------------------------------------
# Capability Gap
# ------------------------------------------------------------------

def _render_capability_gap(result):
    capability_output = result.get("capability_gap_output")

    if not capability_output:
        return

    st.divider()
    st.subheader("🎓 Export Readiness")

    cols = st.columns(2)
    cols[0].metric("Gap Score", f"{capability_output.gap_score}/5")
    cols[1].metric("Capability Distance", capability_output.capability_distance)

    if capability_output.reasoning:
        st.write(capability_output.reasoning)

    if capability_output.missing_requirements:
        st.markdown("**Missing certifications/standards:**")
        for req in capability_output.missing_requirements:
            st.markdown(f"- {req}")

    if capability_output.upgrade_path:
        st.markdown("**Suggested upgrade path:**")
        for step in capability_output.upgrade_path:
            st.markdown(f"- {step}")


# ------------------------------------------------------------------
# Logistics
# ------------------------------------------------------------------

def _render_logistics(result):
    logistics_output = result.get("logistics_output")

    if not logistics_output or not logistics_output.signals:
        return

    st.divider()
    st.subheader("🚢 Logistics")

    for signal in logistics_output.signals:

        cols = st.columns(4)
        cols[0].markdown(f"**{signal.destination_country}**")
        cols[1].metric("Transit", f"{signal.sea_transit_days} days")
        cols[2].metric("Freight cost", f"${signal.freight_cost_usd_per_kg}/kg")
        cols[3].metric("Logistics cost score", signal.logistics_cost_score)


# ------------------------------------------------------------------
# Risk Intelligence
# ------------------------------------------------------------------

def _render_risk(result):
    risk_output = result.get("risk_output")

    if not risk_output or not risk_output.signals:
        return

    st.divider()
    st.subheader("⚠️ Country Risk")

    for signal in risk_output.signals:

        icon, banner_fn = _RISK_LEVEL_STYLE.get(signal.risk_level, ("⚪", st.info))

        flags = []
        if signal.sanctions_flag:
            flags.append("**Sanctions flag active**")
        if not signal.ecgc_cover_available:
            flags.append("No ECGC cover available")

        message = f"{icon} **{signal.destination_country}** — {signal.risk_level} risk ({signal.overall_risk_score})"
        if flags:
            message += "  \n" + " · ".join(flags)
        message += f"  \n{signal.notes}"

        banner_fn(message)


# ------------------------------------------------------------------
# Global Competitor Landscape
# ------------------------------------------------------------------

def _render_competitors(result):
    competitor_output = result.get("competitor_output")

    if not competitor_output or not competitor_output.signals:
        return

    st.divider()
    st.subheader("🌐 Global Competitor Landscape")

    for signal in competitor_output.signals:

        with st.expander(f"{signal.hs_code} → {signal.destination_country}"):

            cols = st.columns(3)
            cols[0].metric("India's Market Share", f"{signal.india_market_share_pct}%")
            cols[1].metric("India's Avg Price", f"${signal.india_avg_price_usd}")
            cols[2].metric("India Priced", signal.price_position.title())

            st.caption(
                f"Market concentration among top competitors: "
                f"{signal.market_concentration * 100:.0f}%"
            )

            st.markdown("**Top competing countries:**")
            for c in signal.top_competitors:
                st.write(f"- {c.country}: {c.market_share_pct}% share @ ${c.avg_price_usd}")


# ------------------------------------------------------------------
# Buyer Discovery
# ------------------------------------------------------------------

def _render_buyer_discovery(result):
    buyer_output = result.get("buyer_discovery_output")

    if not buyer_output or not buyer_output.buyer_personas:
        return

    st.divider()
    st.subheader("🎯 Likely Buyer Personas")
    st.caption(
        "Buyer categories, not specific companies — use these to shape "
        "outreach, not as a contact list."
    )

    for persona in buyer_output.buyer_personas:
        with st.expander(persona.persona_name):
            st.write(persona.description)
            st.caption(f"Typical order size: {persona.typical_order_size}")
            st.caption(f"Procurement notes: {persona.procurement_notes}")

    if buyer_output.recommended_channels:
        st.markdown("**Recommended outreach channels:**")
        for channel in buyer_output.recommended_channels:
            st.markdown(f"- {channel}")

    if buyer_output.outreach_tips:
        st.markdown("**Outreach tips:**")
        for tip in buyer_output.outreach_tips:
            st.markdown(f"- {tip}")


# ------------------------------------------------------------------
# Tariff & FTA Position
# ------------------------------------------------------------------

def _render_fta(result):
    fta_output = result.get("fta_output")

    if not fta_output or not fta_output.signals:
        return

    st.divider()
    st.subheader("📜 Tariff & FTA Position")

    for signal in fta_output.signals:

        with st.expander(f"{signal.hs_code} → {signal.destination_country}"):

            if signal.eligible:
                cols = st.columns(3)
                cols[0].metric("MFN Tariff", f"{signal.mfn_tariff_pct}%")
                cols[1].metric("Preferential Tariff", f"{signal.preferential_tariff_pct}%")
                cols[2].metric("Savings", f"{signal.tariff_savings_pct}pp")
                st.success(f"Eligible under {signal.fta_name}")
                if signal.rules_of_origin:
                    st.caption(f"Rules of origin: {signal.rules_of_origin}")
            else:
                st.info(
                    f"No FTA preference available for this market. "
                    f"Standard MFN tariff of {signal.mfn_tariff_pct}% applies."
                )

            if signal.has_special_duties:
                st.error(
                    f"⚠️ Special duties apply: anti-dumping "
                    f"{signal.anti_dumping_duty_pct}%, countervailing "
                    f"{signal.countervailing_duty_pct}%. "
                    f"These apply on top of the FTA/MFN rate."
                )
                if signal.special_duty_notes:
                    st.caption(signal.special_duty_notes)

            st.metric("Effective Total Tariff", f"{signal.effective_tariff_pct}%")


# ------------------------------------------------------------------
# Document Intelligence
# ------------------------------------------------------------------

def _render_document_intelligence(result):
    doc_output = result.get("document_intelligence_output")

    if not doc_output or not doc_output.checklists:
        return

    st.divider()
    st.subheader("📋 Required Export Documents")

    for checklist in doc_output.checklists:

        with st.expander(checklist.destination_country):

            st.markdown("**Mandatory documents:**")
            for doc in checklist.mandatory_documents:
                st.markdown(f"- {doc}")

            if checklist.conditional_documents:
                st.markdown("**Conditional documents:**")
                for cond in checklist.conditional_documents:
                    st.markdown(f"- **{cond.name}** — {cond.condition}")

            if checklist.notes:
                st.caption(checklist.notes)


# ------------------------------------------------------------------
# Certification Process
# ------------------------------------------------------------------

def _render_certification(result):
    cert_output = result.get("certification_output")

    if not cert_output or not cert_output.certifications:
        return

    st.divider()
    st.subheader("📝 Certification Process")

    for c in cert_output.certifications:
        with st.expander(c.name):
            st.write(f"**Issuing body:** {c.issuing_body}")
            cols = st.columns(2)
            cols[0].metric(
                "Est. Cost", f"${c.cost_usd_range[0]}-${c.cost_usd_range[1]}"
            )
            cols[1].metric(
                "Timeline",
                f"{c.timeline_weeks_range[0]}-{c.timeline_weeks_range[1]} weeks",
            )
            if c.validity_years:
                st.caption(f"Valid for {c.validity_years} year(s), then renewal required.")
            st.markdown("**Application steps:**")
            for step in c.application_steps:
                st.markdown(f"- {step}")


# ------------------------------------------------------------------
# Reference Knowledge (RAG)
# ------------------------------------------------------------------

def _render_rag(result):
    rag_output = result.get("rag_output")

    if not rag_output or not rag_output.snippets:
        return

    st.divider()
    st.subheader("📚 Reference Knowledge")
    st.caption("Background context retrieved to help ground this answer.")

    for s in rag_output.snippets:
        with st.expander(f"{s.title} ({s.source})"):
            st.write(s.text)


# ------------------------------------------------------------------
# Government Schemes
# ------------------------------------------------------------------

def _render_schemes(result):
    scheme_output = result.get("scheme_compliance_output")

    if not scheme_output:
        return

    schemes = scheme_output.eligible_schemes()

    if not schemes:
        return

    st.divider()
    st.subheader("🏛 Government Schemes")

    for scheme in schemes:
        with st.expander(scheme.name):
            st.write(f"**Issued By:** {scheme.issuing_body}")
            st.write(scheme.benefit_summary)


# ------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------

def _render_errors(result):
    errors = result.get("errors")

    if not errors:
        return

    st.divider()
    with st.expander("⚠️ Some agents reported issues", expanded=False):
        for e in errors:
            st.write(f"- {e}")
