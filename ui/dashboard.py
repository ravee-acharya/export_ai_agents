"""
ExportAI decision dashboard.

Redesigned around a simple principle: the person using this is an SME
owner deciding where to sell, not a data analyst. Every section answers
a decision question ("which market?", "what price?", "is it safe?"),
not "here is a table of numbers."

Structure:
  1. Token usage strip (compact, always visible)
  2. Decision hero card — plain-English recommendation, no jargon
  3. Market comparison chart — the one visual that lets someone compare
     markets at a glance without reading anything
  4. Tabs (Overview / Money / Risk & Readiness / Logistics & Buyers /
     Advanced) instead of 17 stacked expanders — nothing scrolls forever
"""

import streamlit as st
import plotly.graph_objects as go

from ui.trade_globe import render_trade_globe
from ui.theme import render_score_ring


_RISK_LEVEL_STYLE = {
    "Low": ("🟢", st.success),
    "Moderate": ("🟡", st.warning),
    "High": ("🟠", st.warning),
    "Severe": ("🔴", st.error),
}

_TEAL = "#3FB8AF"
_BRASS = "#E3A857"
_CORAL = "#E2725B"


def _score_tier(score: float) -> tuple[str, str, str]:
    """Returns (label, color, emoji) for a score, matching the globe's tiers."""
    if score >= 60:
        return "Strong opportunity", _TEAL, "🟢"
    if score >= 30:
        return "Worth exploring", _BRASS, "🟡"
    return "Weak opportunity", _CORAL, "🔴"


def render_dashboard(result):

    if not result:
        return

    _render_token_usage(result)
    _render_decision_hero(result)
    _render_market_comparison_chart(result)

    scores = result.get("opportunity_scores", [])
    tab_names = ["🏆 Overview", "💰 Money", "⚠️ Risk & Readiness", "🚚 Logistics & Buyers"]
    if result.get("errors") or result.get("rag_output"):
        tab_names.append("🔧 Advanced")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_summary(result)
        _render_trade_globe_section(result)
        _render_opportunity_scores(result)

    with tabs[1]:
        _render_pricing(result)
        _render_fta(result)
        _render_schemes(result)

    with tabs[2]:
        _render_risk(result)
        _render_capability_gap(result)
        _render_certification(result)

    with tabs[3]:
        _render_logistics(result)
        _render_document_intelligence(result)
        _render_buyer_discovery(result)
        _render_competitors(result)

    if len(tabs) > 4:
        with tabs[4]:
            _render_rag(result)
            _render_errors(result)


# ------------------------------------------------------------------
# Token Usage Summary (compact strip, always visible)
# ------------------------------------------------------------------

def _render_token_usage(result):
    usage = result.get("token_usage")
    if not usage or not usage.get("per_agent"):
        return

    total = usage.get("total_tokens", 0)
    cost = usage.get("total_cost_usd", 0.0)
    model = usage.get("model", "unknown")
    per_agent = usage.get("per_agent", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🤖 Model", model.split("/")[-1][:20])
    col2.metric("📥 Input Tokens", f"{usage.get('total_input_tokens', 0):,}")
    col3.metric("📤 Output Tokens", f"{usage.get('total_output_tokens', 0):,}")
    col4.metric("💰 Est. Cost", "Free" if cost == 0.0 else f"${cost:.4f}")

    with st.expander(f"📊 Token breakdown by agent ({total:,} total tokens)"):
        for a in per_agent:
            agent_cost = a.get("cost_usd", 0.0)
            cost_str = "free" if agent_cost == 0.0 else f"${agent_cost:.5f}"
            st.markdown(
                f"**{a['agent']}** — "
                f"{a['input_tokens']:,} in + {a['output_tokens']:,} out "
                f"= **{a['total_tokens']:,} tokens** ({cost_str})"
            )

    st.divider()


# ------------------------------------------------------------------
# Decision Hero Card — the single most important thing on the page
# ------------------------------------------------------------------

def _best_market_per_country(scores: list[dict]) -> dict[str, dict]:
    """Aggregate to the single best-scoring row per destination country."""
    best: dict[str, dict] = {}
    for s in scores or []:
        country = s.get("destination_country", "")
        if country not in best or s.get("score", 0) > best[country].get("score", 0):
            best[country] = s
    return best


def _render_decision_hero(result):
    scores = result.get("opportunity_scores", [])
    if not scores:
        return

    best_per_country = _best_market_per_country(scores)
    if not best_per_country:
        return

    top_country, top_score_row = max(
        best_per_country.items(), key=lambda kv: kv[1].get("score", 0)
    )
    top_score = top_score_row.get("score", 0)
    label, color, emoji = _score_tier(top_score)

    # Build plain-English reasons from whatever data is available for
    # the top market — never show raw numbers without a takeaway.
    reasons = []

    breakdown = top_score_row.get("score_breakdown", {})
    growth = breakdown.get("demand_growth_pct")
    if growth is not None:
        try:
            growth_f = float(growth)
            if growth_f > 0:
                reasons.append(f"Demand is growing **{growth_f:.1f}%** year over year")
        except (TypeError, ValueError):
            pass

    pricing_output = result.get("pricing_output")
    if pricing_output and getattr(pricing_output, "pricing", None):
        for p in pricing_output.pricing:
            if p.destination_country == top_country:
                reasons.append(
                    f"You could sell at around **${p.recommended_fob_price}** per unit "
                    f"with a **{p.expected_margin_pct}%** margin"
                )
                break

    risk_output = result.get("risk_output")
    if risk_output and getattr(risk_output, "signals", None):
        for r in risk_output.signals:
            if r.destination_country == top_country:
                if r.risk_level in ("Low", "Moderate"):
                    reasons.append(f"Country risk is **{r.risk_level.lower()}** — a safe market to start with")
                else:
                    reasons.append(f"⚠️ Country risk is **{r.risk_level.lower()}** — plan payment terms carefully")
                break

    logistics_output = result.get("logistics_output")
    if logistics_output and getattr(logistics_output, "signals", None):
        for l in logistics_output.signals:
            if l.destination_country == top_country:
                reasons.append(f"Shipping takes about **{l.sea_transit_days} days** by sea")
                break

    fta_output = result.get("fta_output")
    if fta_output and getattr(fta_output, "signals", None):
        for f in fta_output.signals:
            if f.destination_country == top_country and getattr(f, "eligible", False):
                reasons.append(
                    f"You qualify for a trade agreement discount — "
                    f"**{f.tariff_savings_pct} percentage points** lower duty"
                )
                break

    others = sorted(
        [(c, s.get("score", 0)) for c, s in best_per_country.items() if c != top_country],
        key=lambda x: x[1], reverse=True,
    )

    st.markdown(
        f"""
<div style="
    background: linear-gradient(135deg, rgba(63,184,175,0.12), rgba(227,168,87,0.08));
    border: 1.5px solid {color};
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 8px;
">
  <div style="font-size: 13px; color: #9CA3BF; letter-spacing: 0.5px; text-transform: uppercase;">
    Our Recommendation
  </div>
  <div style="font-size: 28px; font-weight: 700; color: #F6F3EC; margin: 4px 0 2px 0; font-family: Georgia, serif;">
    {emoji} Target <span style="color:{color}">{top_country}</span> first
  </div>
  <div style="font-size: 14px; color: #9CA3BF; margin-bottom: 14px;">
    {label} — Opportunity Score {top_score:.0f}/100
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if reasons:
        st.markdown("**Why:**")
        for r in reasons[:4]:
            st.markdown(f"- {r}")

    if others:
        others_str = ", ".join(f"{c} ({s:.0f})" for c, s in others[:3])
        st.caption(f"Other markets worth a look: {others_str}")

    st.markdown("")


# ------------------------------------------------------------------
# Market Comparison Chart — visual, no reading required
# ------------------------------------------------------------------

def _render_market_comparison_chart(result):
    scores = result.get("opportunity_scores", [])
    best_per_country = _best_market_per_country(scores)

    if len(best_per_country) < 2:
        return  # nothing to compare with only one market

    countries = list(best_per_country.keys())
    values = [best_per_country[c].get("score", 0) for c in countries]
    colors = [_score_tier(v)[1] for v in values]

    # Sort descending so the best market reads first, left to right
    order = sorted(range(len(countries)), key=lambda i: values[i], reverse=True)
    countries = [countries[i] for i in order]
    values = [values[i] for i in order]
    colors = [colors[i] for i in order]

    fig = go.Figure(
        data=[
            go.Bar(
                x=countries,
                y=values,
                marker_color=colors,
                text=[f"{v:.0f}" for v in values],
                textposition="outside",
                textfont=dict(size=16, color="#EDEAE2"),
                hovertemplate="%{x}: %{y:.0f}/100<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="Market Comparison", font=dict(size=16, color="#EDEAE2", family="Georgia, serif")),
        height=280,
        margin=dict(t=50, b=30, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 105], showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                  color="#9CA3BF", title="Opportunity Score"),
        xaxis=dict(color="#EDEAE2", tickfont=dict(size=14)),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("🟢 Strong (60+) · 🟡 Worth exploring (30–60) · 🔴 Weak (under 30)")
    st.divider()


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

def _render_summary(result):
    summary = result.get("summary")
    if summary:
        st.markdown(summary)


# ------------------------------------------------------------------
# Trade Routes Globe
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
# Opportunity Scores (detail, for those who want to dig in)
# ------------------------------------------------------------------

def _render_opportunity_scores(result):
    scores = result.get("opportunity_scores", [])

    if not scores:
        return

    st.divider()
    st.subheader("📊 Score Details")
    st.caption("Tap any market below to see exactly what drove its score.")

    for score in scores:

        breakdown = score.get("score_breakdown", {})
        label, color, emoji = _score_tier(score.get("score", 0))

        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(
                f"**{score['destination_country']}** — HS {score['hs_code']}  \n"
                f"{emoji} {label}"
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

    st.subheader("💰 What Should I Charge?")

    for p in pricing_output.pricing:

        with st.container():
            st.markdown(f"**{p.destination_country}** (HS {p.hs_code})")
            cols = st.columns(4)
            cols[0].metric("Sell at (FOB)", f"${p.recommended_fob_price}")
            cols[1].metric("Your Margin", f"{p.expected_margin_pct}%")
            cols[2].metric("Competitiveness", f"{p.competitiveness_score}/10")
            cols[3].metric("Typical Retail", f"${p.estimated_retail_price}")
            st.caption(
                f"Market average import price: ${p.average_import_price} · "
                f"Average Indian export price: ${p.average_indian_export_price}"
            )
            st.markdown("")


# ------------------------------------------------------------------
# Capability Gap
# ------------------------------------------------------------------

def _render_capability_gap(result):
    capability_output = result.get("capability_gap_output")

    if not capability_output:
        return

    st.subheader("🎓 Are You Ready to Export?")

    gap = capability_output.gap_score
    if gap <= 2:
        st.success(f"You're well-prepared (readiness gap: {gap}/5 — low)")
    elif gap == 3:
        st.warning(f"Some gaps to close (readiness gap: {gap}/5 — moderate)")
    else:
        st.error(f"Significant gaps to close first (readiness gap: {gap}/5 — high)")

    if capability_output.reasoning:
        st.write(capability_output.reasoning)

    if capability_output.missing_requirements:
        st.markdown("**You'll need these certifications:**")
        for req in capability_output.missing_requirements:
            st.markdown(f"- {req}")

    if capability_output.upgrade_path:
        st.markdown("**Steps to close the gap:**")
        for step in capability_output.upgrade_path:
            st.markdown(f"- {step}")

    st.divider()


# ------------------------------------------------------------------
# Logistics
# ------------------------------------------------------------------

def _render_logistics(result):
    logistics_output = result.get("logistics_output")

    if not logistics_output or not logistics_output.signals:
        return

    st.subheader("🚢 Shipping It There")

    for signal in logistics_output.signals:
        cols = st.columns(3)
        cols[0].markdown(f"**{signal.destination_country}**")
        cols[1].metric("Transit Time", f"{signal.sea_transit_days} days")
        cols[2].metric("Freight Cost", f"${signal.freight_cost_usd_per_kg}/kg")

    st.divider()


# ------------------------------------------------------------------
# Risk Intelligence
# ------------------------------------------------------------------

def _render_risk(result):
    risk_output = result.get("risk_output")

    if not risk_output or not risk_output.signals:
        return

    st.subheader("⚠️ Is It Safe?")

    for signal in risk_output.signals:

        icon, banner_fn = _RISK_LEVEL_STYLE.get(signal.risk_level, ("⚪", st.info))

        flags = []
        if signal.sanctions_flag:
            flags.append("**Sanctions in effect — do not proceed without legal advice**")
        if not signal.ecgc_cover_available:
            flags.append("No payment-default insurance (ECGC) available")

        message = f"{icon} **{signal.destination_country}** — {signal.risk_level} risk"
        if flags:
            message += "  \n" + " · ".join(flags)
        message += f"  \n{signal.notes}"

        banner_fn(message)

    st.divider()


# ------------------------------------------------------------------
# Global Competitor Landscape
# ------------------------------------------------------------------

def _render_competitors(result):
    competitor_output = result.get("competitor_output")

    if not competitor_output or not competitor_output.signals:
        return

    st.subheader("🌐 Who Else Is Selling There?")

    for signal in competitor_output.signals:

        with st.expander(f"{signal.destination_country} (HS {signal.hs_code})"):

            cols = st.columns(3)
            cols[0].metric("India's Market Share", f"{signal.india_market_share_pct}%")
            cols[1].metric("India's Avg Price", f"${signal.india_avg_price_usd}")
            cols[2].metric("India Priced", signal.price_position.title())

            st.caption(
                f"Top competitors control {signal.market_concentration * 100:.0f}% of this market"
            )
            st.markdown("**Biggest competing countries:**")
            for c in signal.top_competitors:
                st.write(f"- {c.country}: {c.market_share_pct}% share @ ${c.avg_price_usd}")


# ------------------------------------------------------------------
# Buyer Discovery
# ------------------------------------------------------------------

def _render_buyer_discovery(result):
    buyer_output = result.get("buyer_discovery_output")

    if not buyer_output or not buyer_output.buyer_personas:
        return

    st.subheader("🎯 Who Might Buy From You?")
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
        st.markdown("**Where to find them:**")
        for channel in buyer_output.recommended_channels:
            st.markdown(f"- {channel}")

    if buyer_output.outreach_tips:
        st.markdown("**Tips for reaching out:**")
        for tip in buyer_output.outreach_tips:
            st.markdown(f"- {tip}")


# ------------------------------------------------------------------
# Tariff & FTA Position
# ------------------------------------------------------------------

def _render_fta(result):
    fta_output = result.get("fta_output")

    if not fta_output or not fta_output.signals:
        return

    st.subheader("📜 Import Duties & Trade Deals")

    for signal in fta_output.signals:

        with st.expander(f"{signal.destination_country} (HS {signal.hs_code})"):

            if signal.eligible:
                cols = st.columns(3)
                cols[0].metric("Standard Duty", f"{signal.mfn_tariff_pct}%")
                cols[1].metric("Your Duty (with FTA)", f"{signal.preferential_tariff_pct}%")
                cols[2].metric("You Save", f"{signal.tariff_savings_pct}pp")
                st.success(f"You qualify for a discount under {signal.fta_name}")
                if signal.rules_of_origin:
                    st.caption(f"Rules of origin: {signal.rules_of_origin}")
            else:
                st.info(
                    f"No trade-deal discount available here. "
                    f"Standard duty of {signal.mfn_tariff_pct}% applies."
                )

            if signal.has_special_duties:
                st.error(
                    f"⚠️ Extra duties apply: anti-dumping "
                    f"{signal.anti_dumping_duty_pct}%, countervailing "
                    f"{signal.countervailing_duty_pct}%. "
                    f"These stack on top of the rate above."
                )
                if signal.special_duty_notes:
                    st.caption(signal.special_duty_notes)

            st.metric("Total Duty You'll Actually Pay", f"{signal.effective_tariff_pct}%")


# ------------------------------------------------------------------
# Document Intelligence
# ------------------------------------------------------------------

def _render_document_intelligence(result):
    doc_output = result.get("document_intelligence_output")

    if not doc_output or not doc_output.checklists:
        return

    st.subheader("📋 Paperwork You'll Need")

    for checklist in doc_output.checklists:

        with st.expander(checklist.destination_country):

            st.markdown("**Always required:**")
            for doc in checklist.mandatory_documents:
                st.markdown(f"- {doc}")

            if checklist.conditional_documents:
                st.markdown("**Required in some cases:**")
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

    st.subheader("📝 Getting Certified")

    for c in cert_output.certifications:
        with st.expander(c.name):
            st.write(f"**Issuing body:** {c.issuing_body}")
            cols = st.columns(2)
            cols[0].metric("Est. Cost", f"${c.cost_usd_range[0]}-${c.cost_usd_range[1]}")
            cols[1].metric("Timeline", f"{c.timeline_weeks_range[0]}-{c.timeline_weeks_range[1]} weeks")
            if c.validity_years:
                st.caption(f"Valid for {c.validity_years} year(s), then renewal required.")
            st.markdown("**Steps:**")
            for step in c.application_steps:
                st.markdown(f"- {step}")


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

    st.subheader("🏛 Government Support Available")

    for scheme in schemes:
        with st.expander(scheme.name):
            st.write(f"**Issued By:** {scheme.issuing_body}")
            st.write(scheme.benefit_summary)


# ------------------------------------------------------------------
# Reference Knowledge (RAG)
# ------------------------------------------------------------------

def _render_rag(result):
    rag_output = result.get("rag_output")

    if not rag_output or not rag_output.snippets:
        return

    st.subheader("📚 Reference Knowledge")
    st.caption("Background context retrieved to help ground this answer.")

    for s in rag_output.snippets:
        with st.expander(f"{s.title} ({s.source})"):
            st.write(s.text)


# ------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------

def _render_errors(result):
    errors = result.get("errors")

    if not errors:
        return

    with st.expander("⚠️ Some agents reported issues", expanded=False):
        for e in errors:
            st.write(f"- {e}")
