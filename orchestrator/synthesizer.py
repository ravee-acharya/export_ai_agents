"""
Synthesizer — turns opportunity scores, pricing, and scheme data into
a natural-language summary via the configured LLM.
"""

import json

from agents.pricing_agent import PricingAgentOutput
from agents.scheme_compliance_agent import SchemeComplianceAgentOutput
from agents.risk_agent import RiskAgentOutput
from agents.competitor_agent import CompetitorAgentOutput
from agents.buyer_discovery_agent import BuyerDiscoveryOutput
from agents.fta_agent import FTAAgentOutput
from agents.document_intelligence_agent import DocumentIntelligenceOutput
from agents.certification_agent import CertificationAgentOutput
from agents.rag_agent import RAGAgentOutput
from orchestrator.llm_provider import get_llm
from orchestrator.state import OrchestratorState


def _eligible_scheme_lines(scheme_output: SchemeComplianceAgentOutput | None) -> str:
    if not scheme_output or not scheme_output.eligible_schemes():
        return ""
    return "\n".join(
        f"- {s.name}: {s.benefit_summary}" for s in scheme_output.eligible_schemes()
    )


def _pricing_summary_lines(pricing_output: PricingAgentOutput | None) -> str:
    if not pricing_output or not pricing_output.pricing:
        return ""
    return "\n".join(
        f"- {p.hs_code} -> {p.destination_country}: recommended FOB "
        f"${p.recommended_fob_price}, margin {p.expected_margin_pct}%, "
        f"competitiveness {p.competitiveness_score}/10"
        for p in pricing_output.pricing
    )


def _risk_summary_lines(risk_output: RiskAgentOutput | None) -> str:
    if not risk_output or not risk_output.signals:
        return ""
    lines = []
    for s in risk_output.signals:
        flags = []
        if s.sanctions_flag:
            flags.append("SANCTIONS FLAG")
        if not s.ecgc_cover_available:
            flags.append("no ECGC cover")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        lines.append(
            f"- {s.destination_country}: {s.risk_level} risk "
            f"(overall {s.overall_risk_score}){flag_text} — {s.notes}"
        )
    return "\n".join(lines)


def _competitor_summary_lines(competitor_output: CompetitorAgentOutput | None) -> str:
    if not competitor_output or not competitor_output.signals:
        return ""
    lines = []
    for s in competitor_output.signals:
        top = ", ".join(
            f"{c.country} ({c.market_share_pct}% @ ${c.avg_price_usd})"
            for c in s.top_competitors
        )
        lines.append(
            f"- {s.hs_code} -> {s.destination_country}: India holds "
            f"{s.india_market_share_pct}% share at ${s.india_avg_price_usd} "
            f"(priced {s.price_position} vs. competitors). "
            f"Top competitors: {top}"
        )
    return "\n".join(lines)


def _buyer_discovery_lines(buyer_output: BuyerDiscoveryOutput | None) -> str:
    if not buyer_output or not buyer_output.buyer_personas:
        return ""
    lines = []
    for p in buyer_output.buyer_personas:
        lines.append(
            f"- {p.persona_name}: {p.description} "
            f"(typical order size: {p.typical_order_size})"
        )
    if buyer_output.recommended_channels:
        lines.append(
            "Recommended channels: " + ", ".join(buyer_output.recommended_channels)
        )
    return "\n".join(lines)


def _fta_summary_lines(fta_output: FTAAgentOutput | None) -> str:
    if not fta_output or not fta_output.signals:
        return ""
    lines = []
    for s in fta_output.signals:
        if s.eligible:
            base = (
                f"- {s.hs_code} -> {s.destination_country}: eligible under "
                f"{s.fta_name}, tariff drops from {s.mfn_tariff_pct}% (MFN) to "
                f"{s.preferential_tariff_pct}% ({s.tariff_savings_pct}pp savings). "
                f"Rules of origin: {s.rules_of_origin}"
            )
        else:
            base = (
                f"- {s.hs_code} -> {s.destination_country}: no FTA preference "
                f"available, standard MFN tariff of {s.mfn_tariff_pct}% applies."
            )

        if s.has_special_duties:
            base += (
                f" ADDITIONAL SPECIAL DUTIES APPLY: anti-dumping "
                f"{s.anti_dumping_duty_pct}%, countervailing "
                f"{s.countervailing_duty_pct}%. Effective total tariff: "
                f"{s.effective_tariff_pct}%. {s.special_duty_notes or ''}"
            )
        else:
            base += f" Effective total tariff: {s.effective_tariff_pct}%."

        lines.append(base)
    return "\n".join(lines)


def _document_intelligence_lines(doc_output: DocumentIntelligenceOutput | None) -> str:
    if not doc_output or not doc_output.checklists:
        return ""
    lines = []
    for c in doc_output.checklists:
        mandatory = ", ".join(c.mandatory_documents)
        lines.append(f"- {c.destination_country}: mandatory documents: {mandatory}")
        for cond in c.conditional_documents:
            lines.append(f"  Conditional: {cond.name} — {cond.condition}")
    return "\n".join(lines)


def _certification_lines(cert_output: CertificationAgentOutput | None) -> str:
    if not cert_output or not cert_output.certifications:
        return ""
    lines = []
    for c in cert_output.certifications:
        cost_lo, cost_hi = c.cost_usd_range
        time_lo, time_hi = c.timeline_weeks_range
        lines.append(
            f"- {c.name}: issued by {c.issuing_body}, "
            f"cost ${cost_lo}-${cost_hi}, timeline {time_lo}-{time_hi} weeks"
        )
    return "\n".join(lines)


def _rag_lines(rag_output: RAGAgentOutput | None) -> str:
    if not rag_output or not rag_output.snippets:
        return ""
    lines = []
    for s in rag_output.snippets:
        lines.append(f"- [{s.source}] {s.title}: {s.text}")
    return "\n".join(lines)


def synthesize_node(
    state: OrchestratorState,
    provider: str | None = None,
) -> OrchestratorState:

    llm = get_llm(provider)

    scores = state.get("opportunity_scores", [])
    errors = state.get("errors", [])
    scheme_output: SchemeComplianceAgentOutput | None = state.get(
        "scheme_compliance_output"
    )
    pricing_output: PricingAgentOutput | None = state.get("pricing_output")
    risk_output: RiskAgentOutput | None = state.get("risk_output")
    competitor_output: CompetitorAgentOutput | None = state.get("competitor_output")
    buyer_output: BuyerDiscoveryOutput | None = state.get("buyer_discovery_output")
    fta_output: FTAAgentOutput | None = state.get("fta_output")
    doc_output: DocumentIntelligenceOutput | None = state.get(
        "document_intelligence_output"
    )
    cert_output: CertificationAgentOutput | None = state.get("certification_output")
    rag_output: RAGAgentOutput | None = state.get("rag_output")
    conversation_context = state.get("conversation_context", "")

    if state.get("markets_auto_selected"):
        auto_note = (
            "The user did not name specific target countries in their "
            "question -- you evaluated a representative spread of major "
            f"export markets ({', '.join(state.get('target_countries', []))}) "
            "on their behalf. Say so plainly at the start of your answer "
            "(e.g. 'Since you didn't name specific markets, I evaluated "
            "a few major ones for you:'), so it's clear these were chosen "
            "for the person, not requested by them."
        )
        conversation_context = (
            f"{auto_note}\n\n{conversation_context}" if conversation_context else auto_note
        )

    schemes = _eligible_scheme_lines(scheme_output)
    pricing_lines = _pricing_summary_lines(pricing_output)
    risk_lines = _risk_summary_lines(risk_output)
    competitor_lines = _competitor_summary_lines(competitor_output)
    buyer_lines = _buyer_discovery_lines(buyer_output)
    fta_lines = _fta_summary_lines(fta_output)
    doc_lines = _document_intelligence_lines(doc_output)
    cert_lines = _certification_lines(cert_output)
    rag_lines = _rag_lines(rag_output)

    # IMPORTANT: opportunity_scores requires demand_signal_output to
    # have run, but a query can legitimately ask about only pricing,
    # risk, or certifications without ever needing demand data (the
    # LLM-driven planner correctly narrows agent selection to match a
    # narrow question). Gating the entire summary on `scores` being
    # non-empty would silently discard fully-populated pricing/risk/
    # certification/etc. data whenever the query didn't happen to
    # trigger the Demand Signal Agent -- which is a real, common case,
    # not an edge case. So "is there anything to summarize" is judged
    # across ALL agent outputs, not just scores.
    has_any_data = any(
        [
            scores,
            schemes,
            pricing_lines,
            risk_lines,
            competitor_lines,
            buyer_lines,
            fta_lines,
            doc_lines,
            cert_lines,
        ]
    )

    # --------------------------------------------------
    # Truly nothing to report (e.g. every requested agent errored out)
    # --------------------------------------------------
    if not has_any_data:
        message = "No data was generated for this query."
        if errors:
            message += "\n\nErrors:\n" + "\n".join(errors)
        return {"summary": message}

    # --------------------------------------------------
    # Scheme-only response: scores absent, but a narrowly-scoped
    # schemes question was answered -- keep this shorter, focused
    # format rather than routing it through the full opportunity
    # summary prompt below (which would ask the LLM to comment on
    # sections that are empty).
    # --------------------------------------------------
    only_schemes = (
        not scores
        and scheme_output
        and scheme_output.eligible_schemes()
        and not any(
            [
                pricing_lines, risk_lines, competitor_lines,
                buyer_lines, fta_lines, doc_lines, cert_lines,
            ]
        )
    )
    if only_schemes:
        from prompts.manager import render_prompt
        prompt = render_prompt("synthesizer_schemes", schemes=schemes)
        response = llm.invoke(prompt)
        try:
            from orchestrator.token_tracker import record_usage
            record_usage("synthesizer", response)
        except Exception:
            pass
        return {"summary": response.content.strip()}

    # --------------------------------------------------
    # General summary: built from whatever sections have data. Each
    # section is explicitly marked "(not requested/computed for this
    # query)" when empty so the LLM doesn't invent content for it or
    # apologize about it -- it just omits that topic naturally.
    # --------------------------------------------------
    scores_json = json.dumps(scores, indent=2) if scores else ""

    context_block = (
        f"""
Prior Conversation Context (for continuity -- do not repeat verbatim,
just stay consistent with it)

{conversation_context}
"""
        if conversation_context
        else ""
    )

    from prompts.manager import render_prompt
    prompt = render_prompt(
        "synthesizer_main",
        context_block=context_block,
        scores_json=scores_json or "(not computed for this query -- the question didn't require a full opportunity assessment)",
        pricing_lines=pricing_lines or "(not requested for this query)",
        risk_lines=risk_lines or "(not requested for this query)",
        competitor_lines=competitor_lines or "(not requested for this query)",
        buyer_lines=buyer_lines or "(not requested for this query)",
        fta_lines=fta_lines or "(not requested for this query)",
        doc_lines=doc_lines or "(not requested for this query)",
        cert_lines=cert_lines or "(not requested for this query)",
        rag_lines=rag_lines or "(none retrieved)",
        schemes=schemes or "(not requested for this query)",
    )

    response = llm.invoke(prompt)
    try:
        from orchestrator.token_tracker import record_usage
        record_usage("synthesizer", response)
    except Exception:
        pass
    return {"summary": response.content.strip()}
