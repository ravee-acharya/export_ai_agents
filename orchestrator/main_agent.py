"""
Main orchestrator agent.
"""

import json

from langgraph.graph import END, StateGraph

from agents.demand_signal_agent import (
    DemandSignalAgentOutput,
    run_demand_signal_agent,
)
from agents.scheme_compliance_agent import (
    SchemeComplianceAgentOutput,
    run_scheme_compliance_agent,
)

from orchestrator.llm_provider import get_llm
from orchestrator.query_parser import parse_query
from orchestrator.state import (
    OpportunityScore,
    OrchestratorState,
)

PLACEHOLDER_IMPORT_GAP = 0.6
PLACEHOLDER_PRICE_PREMIUM = 1.15
PLACEHOLDER_CAPABILITY_DISTANCE = 0.4
PLACEHOLDER_LOGISTICS_COST = 0.3

AVAILABLE_AGENTS = {
    "demand_signal": "Demand Signal Agent",
    "scheme_compliance": "Scheme & Compliance Agent",
}


def parse_query_node(
    state: OrchestratorState,
    provider: str | None = None,
) -> OrchestratorState:

    # Structured input
    if state.get("sector") and state.get("target_countries"):
        return {
            "sector": state["sector"],
            "hs_codes": state["hs_codes"],
            "target_countries": state["target_countries"],
            "sme_revenue_cr": state.get("sme_revenue_cr"),
            "has_udyam_registration": state.get(
                "has_udyam_registration",
                True,
            ),
            "agents_to_call": list(
                AVAILABLE_AGENTS.keys()
            ),
        }

    query = state.get("query", "").strip()

    if not query:
        return {
            "errors": [
                "No query provided."
            ],
            "agents_to_call": [],
        }

    try:

        parsed = parse_query(
            query=query,
            provider=provider,
        )

        return {
            "sector": parsed["sector"],
            "hs_codes": parsed["hs_codes"],
            "target_countries": parsed["target_countries"],
            "sme_revenue_cr": parsed.get(
                "sme_revenue_cr"
            ),
            "has_udyam_registration": parsed.get(
                "has_udyam_registration",
                True,
            ),
            "agents_to_call": parsed.get(
                "agents_to_call",
                list(AVAILABLE_AGENTS.keys()),
            ),
        }

    except Exception as ex:

        return {
            "errors": [
                f"Query parsing failed: {ex}"
            ],
            "agents_to_call": [],
        }
# ------------------------------------------------------------------
# Safe Agent Execution
# ------------------------------------------------------------------


def _safe_call(agent_name: str, fn, *args, **kwargs):

    try:
        return fn(*args, **kwargs), None

    except Exception as ex:
        return (
            None,
            f"{agent_name} failed: {ex}",
        )


# ------------------------------------------------------------------
# Execute Sub Agents
# ------------------------------------------------------------------


def call_sub_agents_node(
    state: OrchestratorState,
) -> OrchestratorState:

    updates: OrchestratorState = {}

    errors = list(
        state.get("errors", [])
    )

    agents = state.get(
        "agents_to_call",
        [],
    )

    if "demand_signal" in agents:

        result, error = _safe_call(
            "Demand Signal Agent",
            run_demand_signal_agent,
            sector=state["sector"],
            hs_codes=state["hs_codes"],
            target_countries=state["target_countries"],
        )

        if error:
            errors.append(error)

        updates["demand_signal_output"] = result

    if "scheme_compliance" in agents:

        result, error = _safe_call(
            "Scheme Compliance Agent",
            run_scheme_compliance_agent,
            sector=state["sector"],
            target_countries=state["target_countries"],
            sme_revenue_cr=state.get(
                "sme_revenue_cr"
            ),
            has_udyam_registration=state.get(
                "has_udyam_registration",
                True,
            ),
        )

        if error:
            errors.append(error)

        updates["scheme_compliance_output"] = result

    updates["errors"] = errors

    return updates
# ------------------------------------------------------------------
# Compute Opportunity Scores
# ------------------------------------------------------------------


def compute_scores_node(
    state: OrchestratorState,
) -> OrchestratorState:

    demand_output: DemandSignalAgentOutput | None = state.get(
        "demand_signal_output"
    )

    if (
        demand_output is None
        or not demand_output.signals
    ):
        return {
            "opportunity_scores": [],
        }

    scores: list[OpportunityScore] = []

    for signal in demand_output.signals:

        demand_growth = max(
            signal.growth_rate_pct / 100,
            0.01,
        )

        competition_density = (
            signal.competition_density_score
        )

        import_gap = PLACEHOLDER_IMPORT_GAP
        price_premium = PLACEHOLDER_PRICE_PREMIUM
        capability_distance = PLACEHOLDER_CAPABILITY_DISTANCE
        logistics_cost = PLACEHOLDER_LOGISTICS_COST

        numerator = (
            demand_growth
            * import_gap
            * price_premium
        )

        denominator = (
            capability_distance
            + competition_density
            + logistics_cost
        )

        raw_score = (
            numerator / denominator
            if denominator > 0
            else 0
        )

        score = round(
            min(raw_score * 60, 100),
            1,
        )

        scores.append(
            {
                "hs_code": signal.hs_code,
                "destination_country": signal.destination_country,
                "score": score,
                "score_breakdown": {
                    "demand_growth_pct": signal.growth_rate_pct,
                    "surge_detected": signal.surge_detected,
                    "competition_density": competition_density,
                    "active_indian_suppliers": signal.active_indian_suppliers,
                    "import_gap": import_gap,
                    "price_premium": price_premium,
                    "capability_distance": capability_distance,
                    "logistics_cost": logistics_cost,
                },
                "note": (
                    "Demand and competition use live data. "
                    "Remaining factors are placeholders."
                ),
            }
        )

    scores.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return {
        "opportunity_scores": scores,
    }
# ------------------------------------------------------------------
# Summary Generation
# ------------------------------------------------------------------


def synthesize_node(
    state: OrchestratorState,
    provider: str | None = None,
) -> OrchestratorState:

    llm = get_llm(provider)

    scores = state.get(
        "opportunity_scores",
        [],
    )

    errors = state.get(
        "errors",
        [],
    )

    scheme_output: SchemeComplianceAgentOutput | None = state.get(
        "scheme_compliance_output"
    )

    # --------------------------------------------------
    # Scheme-only response
    # --------------------------------------------------

    if (
        not scores
        and scheme_output
        and scheme_output.eligible_schemes()
    ):

        schemes = "\n".join(
            [
                f"- {s.name}: {s.benefit_summary}"
                for s in scheme_output.eligible_schemes()
            ]
        )

        prompt = f"""
You are ExportAI.

The user requested government schemes.

Available schemes:

{schemes}

Write a concise summary.

Mention:

- Best schemes
- Key benefits
- Who should apply

Maximum 150 words.
"""

        response = llm.invoke(prompt)

        return {
            "summary": response.content.strip()
        }

    # --------------------------------------------------
    # Nothing generated
    # --------------------------------------------------

    if not scores:

        message = "No opportunity data was generated."

        if errors:
            message += "\n\nErrors:\n"
            message += "\n".join(errors)

        return {
            "summary": message
        }

    # --------------------------------------------------
    # Export opportunity summary
    # --------------------------------------------------

    scores_json = json.dumps(
        scores,
        indent=2,
    )

    schemes = ""

    if (
        scheme_output
        and scheme_output.eligible_schemes()
    ):

        schemes = "\n".join(
            [
                s.name
                for s in scheme_output.eligible_schemes()
            ]
        )

    prompt = f"""
You are ExportAI.

Opportunity Scores

{scores_json}

Government Schemes

{schemes}

Write an export opportunity summary.

Mention:

- Best market
- Demand trend
- Competition
- Best government scheme

Maximum 200 words.
"""

    response = llm.invoke(prompt)

    return {
        "summary": response.content.strip()
    }
# ------------------------------------------------------------------
# Build Graph
# ------------------------------------------------------------------


def build_graph(
    provider: str | None = None,
):

    # Validate provider
    get_llm(provider)

    graph = StateGraph(
        OrchestratorState
    )

    graph.add_node(
        "parse_query",
        lambda state: parse_query_node(
            state,
            provider,
        ),
    )

    graph.add_node(
        "call_sub_agents",
        call_sub_agents_node,
    )

    graph.add_node(
        "compute_scores",
        compute_scores_node,
    )

    graph.add_node(
        "synthesize",
        lambda state: synthesize_node(
            state,
            provider,
        ),
    )

    graph.set_entry_point(
        "parse_query"
    )

    graph.add_edge(
        "parse_query",
        "call_sub_agents",
    )

    graph.add_edge(
        "call_sub_agents",
        "compute_scores",
    )

    graph.add_edge(
        "compute_scores",
        "synthesize",
    )

    graph.add_edge(
        "synthesize",
        END,
    )

    return graph.compile()
# ------------------------------------------------------------------
# Convenience Helpers
# ------------------------------------------------------------------


def analyze_query(
    query: str,
    provider: str | None = None,
):

    app = build_graph(provider)

    return app.invoke(
        {
            "query": query,
        }
    )


def analyze_structured(
    *,
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
    sme_revenue_cr: float | None = None,
    has_udyam_registration: bool = True,
    provider: str | None = None,
):

    app = build_graph(provider)

    return app.invoke(
        {
            "sector": sector,
            "hs_codes": hs_codes,
            "target_countries": target_countries,
            "sme_revenue_cr": sme_revenue_cr,
            "has_udyam_registration": has_udyam_registration,
        }
    )
# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------


def health_check(
    provider: str | None = None,
) -> dict:

    try:

        get_llm(provider)

        return {
            "status": "ok",
            "provider": provider or "default",
        }

    except Exception as ex:

        return {
            "status": "error",
            "error": str(ex),
        }
# ------------------------------------------------------------------
# Smoke Test
# ------------------------------------------------------------------

if __name__ == "__main__":

    result = analyze_query(
        "I manufacture cotton towels and want to export to Germany.",
        provider="gemini",
    )

    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(result.get("summary"))

    print("\n")
    print("=" * 80)
    print("OPPORTUNITY SCORES")
    print("=" * 80)

    for score in result.get("opportunity_scores", []):

        print(
            f"{score['hs_code']} -> "
            f"{score['destination_country']} "
            f"({score['score']})"
        )

    print("\n")
    print("=" * 80)
    print("DONE")
    print("=" * 80)