"""
Agent registry — single source of truth for which sub-agents exist,
how to call them, where their output goes in state, and how the
query parser auto-selects them from natural language.

Adding a new agent should mean: write the agent module, add one entry
here. Nothing else in the orchestrator (dispatcher, planner, scorer)
should need editing for a new *deterministic* sub-agent to start
running. (Scoring logic that actually *uses* an agent's output, like
scorer.py consulting pricing_output, is a separate, deliberate step —
the registry only handles wiring the agent into the graph.)

Before this file existed, adding an agent meant touching:
  - AVAILABLE_AGENTS dict in main_agent.py
  - the if-chain in call_sub_agents_node
  - compute_scores_node's placeholder constants
  - state.py (already handled, that file was ahead of the code)
  - query_parser._detect_agents's hardcoded keyword logic
That's now down to: add an AgentSpec here, add an input builder here,
and (only if the agent should influence scoring) update scorer.py.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from agents.demand_signal_agent import run_demand_signal_agent
from agents.pricing_agent import run_pricing_agent
from agents.scheme_compliance_agent import run_scheme_compliance_agent
from agents.capability_gap_agent import run_capability_gap_agent
from agents.logistics_agent import run_logistics_agent
from agents.risk_agent import run_risk_agent
from agents.competitor_agent import run_competitor_agent
from agents.buyer_discovery_agent import run_buyer_discovery_agent
from agents.fta_agent import run_fta_agent
from agents.document_intelligence_agent import run_document_intelligence_agent
from agents.certification_agent import run_certification_agent
from agents.rag_agent import run_rag_agent
from agents.forecast_agent import run_forecast_agent


@dataclass(frozen=True)
class AgentSpec:
    name: str
    display_name: str
    run_fn: Callable[..., Any]
    state_key: str  # where output is stored in OrchestratorState
    keywords: tuple[str, ...] = field(default_factory=tuple)
    default: bool = True  # included when no keyword override applies
    exclusive: bool = False  # if keywords match, ONLY this agent runs


# ------------------------------------------------------------------
# Input builders — map orchestrator state -> this agent's run_fn kwargs.
# Kept separate from AgentSpec so run_fn signatures don't have to match
# state field names 1:1.
# ------------------------------------------------------------------


def _demand_signal_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "hs_codes": state["hs_codes"],
        "target_countries": state["target_countries"],
    }


def _scheme_compliance_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
        "sme_revenue_cr": state.get("sme_revenue_cr"),
        "has_udyam_registration": state.get("has_udyam_registration", True),
    }


def _pricing_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "hs_codes": state["hs_codes"],
        "target_countries": state["target_countries"],
    }


def _capability_gap_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
        "sme_certifications": state.get("sme_certifications", []),
        # LLM-backed agent — needs the provider, unlike the
        # deterministic agents above. Planner stores this in state.
        "provider": state.get("provider"),
    }


def _logistics_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
    }


def _risk_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
    }


def _competitor_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "hs_codes": state["hs_codes"],
        "target_countries": state["target_countries"],
    }


def _buyer_discovery_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
        "hs_codes": state.get("hs_codes", []),
        # LLM-backed agent — needs the provider, same as Capability Gap.
        "provider": state.get("provider"),
    }


def _fta_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "hs_codes": state["hs_codes"],
        "target_countries": state["target_countries"],
    }


def _document_intelligence_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
    }


def _certification_inputs(state: dict) -> dict:
    return {
        "sector": state["sector"],
        "target_countries": state["target_countries"],
    }


def _rag_inputs(state: dict) -> dict:
    # Retrieval needs the raw query text for relevance; when the
    # request came through the structured input path (no free-text
    # query), fall back to a synthetic query built from sector +
    # countries so retrieval still has something to work with.
    query_text = state.get("query") or (
        f"{state.get('sector', '')} export to "
        f"{', '.join(state.get('target_countries', []))}"
    )
    return {
        "query": query_text,
        "sector": state.get("sector"),
    }


def _forecast_inputs(state: dict) -> dict:
    return {
        "sector": state.get("sector", "general"),
        "hs_codes": state.get("hs_codes", []),
        "target_countries": state.get("target_countries", []),
    }


INPUT_BUILDERS: dict[str, Callable[[dict], dict]] = {
    "demand_signal": _demand_signal_inputs,
    "scheme_compliance": _scheme_compliance_inputs,
    "pricing": _pricing_inputs,
    "capability_gap": _capability_gap_inputs,
    "logistics": _logistics_inputs,
    "risk": _risk_inputs,
    "competitor": _competitor_inputs,
    "buyer_discovery": _buyer_discovery_inputs,
    "fta": _fta_inputs,
    "document_intelligence": _document_intelligence_inputs,
    "certification": _certification_inputs,
    "rag": _rag_inputs,
    "forecast": _forecast_inputs,
}


AGENT_REGISTRY: dict[str, AgentSpec] = {
    "demand_signal": AgentSpec(
        name="demand_signal",
        display_name="Demand Signal Agent",
        run_fn=run_demand_signal_agent,
        state_key="demand_signal_output",
        default=True,
    ),
    "scheme_compliance": AgentSpec(
        name="scheme_compliance",
        display_name="Scheme & Compliance Agent",
        run_fn=run_scheme_compliance_agent,
        state_key="scheme_compliance_output",
        keywords=(
            "scheme", "schemes", "subsidy", "subsidies", "government",
            "benefit", "benefits", "rodtep", "pli", "incentive", "incentives",
        ),
        default=True,
        # A query that's purely about schemes shouldn't also run
        # demand/pricing — mirrors the original query_parser behavior.
        exclusive=True,
    ),
    "pricing": AgentSpec(
        name="pricing",
        display_name="Pricing Agent",
        run_fn=run_pricing_agent,
        state_key="pricing_output",
        keywords=(
            "price", "pricing", "prices", "margin", "margins", "fob",
            "competitor price", "competitive price", "retail price",
        ),
        default=True,
    ),
    "capability_gap": AgentSpec(
        name="capability_gap",
        display_name="Capability Gap Agent",
        run_fn=run_capability_gap_agent,
        state_key="capability_gap_output",
        keywords=(
            "certification", "certified", "certificate", "iso",
            "compliance standard", "capability gap", "quality standard",
            "readiness", "am i ready", "do i qualify",
        ),
        default=True,
    ),
    "logistics": AgentSpec(
        name="logistics",
        display_name="Logistics Agent",
        run_fn=run_logistics_agent,
        state_key="logistics_output",
        keywords=(
            "logistics", "shipping", "freight", "transit time",
            "customs clearance", "delivery time", "shipping cost",
        ),
        default=True,
    ),
    "risk": AgentSpec(
        name="risk",
        display_name="Risk Intelligence Agent",
        run_fn=run_risk_agent,
        state_key="risk_output",
        keywords=(
            "risk", "risky", "safe to export", "payment risk",
            "political risk", "sanctions", "currency risk",
            "default risk", "is it safe",
        ),
        default=True,
    ),
    "competitor": AgentSpec(
        name="competitor",
        display_name="Competitor Agent",
        run_fn=run_competitor_agent,
        state_key="competitor_output",
        keywords=(
            "competitor", "competitors", "competition from", "who competes",
            "market share", "china", "vietnam", "bangladesh",
        ),
        default=True,
    ),
    "buyer_discovery": AgentSpec(
        name="buyer_discovery",
        display_name="Buyer Discovery Agent",
        run_fn=run_buyer_discovery_agent,
        state_key="buyer_discovery_output",
        keywords=(
            "buyer", "buyers", "find buyers", "who buys", "customers",
            "importers", "distributors", "leads", "buyer discovery",
        ),
        default=True,
    ),
    "fta": AgentSpec(
        name="fta",
        display_name="Tariff & FTA Agent",
        run_fn=run_fta_agent,
        state_key="fta_output",
        keywords=(
            "fta", "free trade agreement", "tariff", "duty", "customs duty",
            "import duty", "preferential tariff", "cepa", "ceca",
            "anti-dumping", "antidumping", "countervailing", "safeguard duty",
        ),
        default=True,
    ),
    "document_intelligence": AgentSpec(
        name="document_intelligence",
        display_name="Document Intelligence Agent",
        run_fn=run_document_intelligence_agent,
        state_key="document_intelligence_output",
        keywords=(
            "documents", "documentation", "paperwork", "export documents",
            "customs documents", "certificate of origin", "bill of lading",
            "shipping bill", "packing list", "what documents",
        ),
        default=True,
    ),
    "certification": AgentSpec(
        name="certification",
        display_name="Certification Agent",
        run_fn=run_certification_agent,
        state_key="certification_output",
        keywords=(
            "certification process", "how to get certified", "certification cost",
            "certification timeline", "apply for iso", "get certified",
            "how do i certify",
        ),
        default=True,
    ),
    "rag": AgentSpec(
        name="rag",
        display_name="RAG Agent",
        run_fn=run_rag_agent,
        state_key="rag_output",
        keywords=(),  # always runs by default; retrieval has no exclusive trigger
        default=True,
    ),
    "forecast": AgentSpec(
        name="forecast",
        display_name="Forecast Agent",
        run_fn=run_forecast_agent,
        state_key="forecast_output",
        keywords=("forecast", "predict", "projection", "next year", "future",
                  "trend", "3 months", "6 months", "12 months"),
        exclusive=False,
        default=True,   # runs alongside demand signal for every opportunity query
    ),
}


def default_agents() -> list[str]:
    """Agents that run when nothing in the query overrides the selection."""
    return [name for name, spec in AGENT_REGISTRY.items() if spec.default]


def detect_agents_from_query(query: str) -> list[str]:
    """
    Data-driven replacement for the old query_parser._detect_agents.
    An 'exclusive' agent whose keywords match wins outright (e.g. a
    schemes-only question shouldn't also trigger demand/pricing).
    Otherwise, fall back to the default agent set.
    """
    q = query.lower()

    exclusive_matches = [
        name for name, spec in AGENT_REGISTRY.items()
        if spec.exclusive and any(kw in q for kw in spec.keywords)
    ]

    if exclusive_matches:
        return exclusive_matches

    return default_agents()
