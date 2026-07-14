"""
Unit tests for orchestrator/synthesizer.py.

The core scenario under test here is a real bug: a narrowly-scoped
query (e.g. "what about pricing, risk, and certifications?") can
legitimately cause the planner to skip the Demand Signal Agent, which
means opportunity_scores comes back empty -- but pricing/risk/
certification data can still be fully populated. The synthesizer must
build a summary from whatever data exists, not discard everything just
because scores happened to be empty.
"""

from unittest.mock import MagicMock

from agents.pricing_agent import PricingAgentOutput, PricingSignal
from agents.risk_agent import RiskAgentOutput, RiskSignal
from agents.certification_agent import CertificationAgentOutput, CertificationProcess
from agents.scheme_compliance_agent import SchemeComplianceAgentOutput, SchemeMatch
from orchestrator.synthesizer import synthesize_node


def _fake_llm(response_text="stub summary"):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=response_text)
    return llm


def _pricing_output():
    return PricingAgentOutput(
        pricing=[
            PricingSignal(
                hs_code="6302", destination_country="US",
                average_import_price=8.6, average_indian_export_price=6.1,
                estimated_retail_price=22.4, recommended_fob_price=6.59,
                expected_margin_pct=8.0, competitiveness_score=10.0,
            )
        ]
    )


def _risk_output():
    return RiskAgentOutput(
        sector="textiles",
        signals=[
            RiskSignal(
                destination_country="US", political_risk_score=0.15,
                currency_volatility_score=0.2, payment_default_risk_score=0.1,
                overall_risk_score=0.15, risk_level="Low",
                sanctions_flag=False, ecgc_cover_available=True,
                notes="Stable market.",
            )
        ]
    )


def _cert_output():
    return CertificationAgentOutput(
        sector="textiles",
        certifications=[
            CertificationProcess(
                name="ISO 9001", issuing_body="BSI",
                cost_usd_range=(1500, 4000), timeline_weeks_range=(8, 16),
                validity_years=3, application_steps=["Gap analysis", "Audit"],
            )
        ],
    )


def test_narrow_query_with_no_scores_still_produces_real_summary(monkeypatch):
    # This is the exact bug: opportunity_scores empty, but pricing,
    # risk, and certification data are all present. The old code
    # returned "No opportunity data was generated" and threw all of
    # this away.
    fake_llm = _fake_llm("Summary covering pricing, risk, and certification.")
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    state = {
        "opportunity_scores": [],
        "pricing_output": _pricing_output(),
        "risk_output": _risk_output(),
        "certification_output": _cert_output(),
    }

    result = synthesize_node(state)

    assert result["summary"] == "Summary covering pricing, risk, and certification."
    # Confirm the LLM was actually given the real data, not told it's missing.
    prompt = fake_llm.invoke.call_args[0][0]
    assert "6.59" in prompt  # pricing data reached the prompt
    assert "Low" in prompt  # risk data reached the prompt
    assert "ISO 9001" in prompt  # certification data reached the prompt
    assert "No opportunity data was generated" not in result["summary"]


def test_truly_empty_state_returns_graceful_message(monkeypatch):
    fake_llm = _fake_llm()
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    result = synthesize_node({})

    assert "No data was generated" in result["summary"]
    # No data at all -- LLM shouldn't even be called for a fabricated summary.
    fake_llm.invoke.assert_not_called()


def test_truly_empty_state_includes_errors_if_present(monkeypatch):
    fake_llm = _fake_llm()
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    result = synthesize_node({"errors": ["Demand Signal Agent failed: timeout"]})

    assert "Demand Signal Agent failed" in result["summary"]


def test_schemes_only_query_uses_focused_prompt(monkeypatch):
    fake_llm = _fake_llm("Scheme-focused summary.")
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    scheme_output = SchemeComplianceAgentOutput(
        sector="textiles",
        sme_revenue_cr=40,
        matched_schemes=[
            SchemeMatch(
                scheme_id="A", name="Test Scheme", issuing_body="DGFT",
                benefit_summary="Test benefit", eligible=True,
                eligibility_notes="ok", application_notes="apply here",
            )
        ],
    )

    result = synthesize_node({"scheme_compliance_output": scheme_output})

    assert result["summary"] == "Scheme-focused summary."
    prompt = fake_llm.invoke.call_args[0][0]
    assert "government schemes" in prompt.lower()


def test_scores_present_produces_full_summary(monkeypatch):
    fake_llm = _fake_llm("Full opportunity summary.")
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    state = {
        "opportunity_scores": [
            {
                "hs_code": "6302", "destination_country": "US", "score": 45.0,
                "score_breakdown": {}, "note": "test",
            }
        ],
    }

    result = synthesize_node(state)
    assert result["summary"] == "Full opportunity summary."
    prompt = fake_llm.invoke.call_args[0][0]
    assert "45.0" in prompt


def test_conversation_context_included_when_present(monkeypatch):
    fake_llm = _fake_llm()
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    state = {
        "pricing_output": _pricing_output(),
        "conversation_context": "Turn 1: asked about cotton towels to US.",
    }

    synthesize_node(state)
    prompt = fake_llm.invoke.call_args[0][0]
    assert "cotton towels to US" in prompt


def test_empty_sections_marked_not_requested_not_missing(monkeypatch):
    # The LLM shouldn't be told data is "missing" for topics that were
    # never asked about -- it should look like those topics simply
    # weren't part of the question.
    fake_llm = _fake_llm()
    monkeypatch.setattr("orchestrator.synthesizer.get_llm", lambda provider=None: fake_llm)

    state = {"pricing_output": _pricing_output()}
    synthesize_node(state)

    prompt = fake_llm.invoke.call_args[0][0]
    assert "not requested for this query" in prompt
