"""
Graph assembly — builds the LangGraph StateGraph from the four nodes:
planner -> call_sub_agents (dispatcher) -> compute_scores (scorer) ->
synthesize (synthesizer) -> END.

This is what used to be main_agent.py. main_agent.py is now a thin
backward-compatible shim that re-exports everything from here, so
run_demo.py and export_service.py don't need to change their imports
immediately (though pointing them at orchestrator.graph directly is
recommended next cleanup).
"""

from langgraph.graph import END, StateGraph

from orchestrator.dispatcher import call_sub_agents_node
from orchestrator.llm_provider import get_llm
from orchestrator.planner import planner_node
from orchestrator.scorer import compute_scores_node
from orchestrator.state import OrchestratorState
from orchestrator.synthesizer import synthesize_node


def build_graph(provider: str | None = None):

    # Fail fast on a bad/missing provider key before building the graph.
    get_llm(provider)

    graph = StateGraph(OrchestratorState)

    graph.add_node("planner", lambda state: planner_node(state, provider))
    graph.add_node("call_sub_agents", call_sub_agents_node)
    graph.add_node("compute_scores", compute_scores_node)
    graph.add_node("synthesize", lambda state: synthesize_node(state, provider))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "call_sub_agents")
    graph.add_edge("call_sub_agents", "compute_scores")
    graph.add_edge("compute_scores", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


# ------------------------------------------------------------------
# Convenience helpers
# ------------------------------------------------------------------


def analyze_query(query: str, provider: str | None = None):
    app = build_graph(provider)
    return app.invoke({"query": query})


def analyze_structured(
    *,
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
    sme_revenue_cr: float | None = None,
    has_udyam_registration: bool = True,
    sme_certifications: list[str] | None = None,
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
            "sme_certifications": sme_certifications or [],
        }
    )


def health_check(provider: str | None = None) -> dict:
    try:
        get_llm(provider)
        return {"status": "ok", "provider": provider or "default"}
    except Exception as ex:
        return {"status": "error", "error": str(ex)}


# ------------------------------------------------------------------
# Smoke test
# ------------------------------------------------------------------

if __name__ == "__main__":

    result = analyze_query(
        "I manufacture cotton towels and want to export to Germany. "
        "What pricing should I target?",
        provider="gemini",
    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(result.get("summary"))

    print("\n" + "=" * 80)
    print("OPPORTUNITY SCORES")
    print("=" * 80)
    for score in result.get("opportunity_scores", []):
        print(
            f"{score['hs_code']} -> {score['destination_country']} "
            f"({score['score']})"
        )

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
