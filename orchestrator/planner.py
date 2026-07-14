"""
Planner — the graph's entry node. Resolves structured input or a
natural-language query into a normalized request (sector, HS codes,
target countries, SME profile) plus the list of agents to run.

This is the old parse_query_node, renamed to match its actual job and
now delegating agent selection to the registry instead of a hardcoded
default list.
"""

from orchestrator.query_parser import parse_query
from orchestrator.registry import default_agents
from orchestrator.state import OrchestratorState


def planner_node(
    state: OrchestratorState,
    provider: str | None = None,
) -> OrchestratorState:

    # Structured input path — sector/countries already provided.
    if state.get("sector") and state.get("target_countries"):
        return {
            "sector": state["sector"],
            "hs_codes": state["hs_codes"],
            "target_countries": state["target_countries"],
            "sme_revenue_cr": state.get("sme_revenue_cr"),
            "has_udyam_registration": state.get("has_udyam_registration", True),
            "sme_certifications": state.get("sme_certifications", []),
            "provider": provider,
            "conversation_context": state.get("conversation_context", ""),
            "agents_to_call": default_agents(),
        }

    query = state.get("query", "").strip()

    if not query:
        return {"errors": ["No query provided."], "agents_to_call": []}

    try:
        parsed = parse_query(
            query=query,
            provider=provider,
            conversation_context=state.get("conversation_context", ""),
        )

        return {
            "sector": parsed["sector"],
            "hs_codes": parsed["hs_codes"],
            "target_countries": parsed["target_countries"],
            "sme_revenue_cr": parsed.get("sme_revenue_cr"),
            "has_udyam_registration": parsed.get("has_udyam_registration", True),
            # parse_query() only extracts sector/countries/HS codes/revenue
            # from free text — it has no notion of certifications, so if
            # the caller passed sme_certifications alongside the query
            # (e.g. from a UI field), that's the only source for it here.
            "sme_certifications": state.get("sme_certifications", []),
            "provider": provider,
            "conversation_context": state.get("conversation_context", ""),
            "agents_to_call": parsed.get("agents_to_call", default_agents()),
        }

    except Exception as ex:
        return {"errors": [f"Query parsing failed: {ex}"], "agents_to_call": []}
