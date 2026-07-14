"""
Backward-compatible shim.

main_agent.py used to contain the entire orchestrator: parsing,
dispatch, scoring, synthesis, and graph assembly all in one file. It's
now split into planner.py, dispatcher.py, scorer.py, synthesizer.py,
and graph.py (see orchestrator/graph.py for the assembly).

This file re-exports the same public names so existing callers
(run_demo.py, services/export_service.py) keep working unchanged.
New code should import from orchestrator.graph directly instead of
this module — this shim is a migration aid, not a permanent home.
"""

from orchestrator.graph import (
    analyze_query,
    analyze_structured,
    build_graph,
    health_check,
)

__all__ = [
    "analyze_query",
    "analyze_structured",
    "build_graph",
    "health_check",
]
