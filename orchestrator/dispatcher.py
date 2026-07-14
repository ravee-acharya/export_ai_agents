"""
Dispatcher — executes whichever sub-agents the planner selected.

Generic over orchestrator/registry.py: this file does not need to
change when a new agent is added to the registry. It only knows how to
look up a spec, build inputs, call it safely, and store the result.
"""

from orchestrator.registry import AGENT_REGISTRY, INPUT_BUILDERS
from orchestrator.state import OrchestratorState


def _safe_call(agent_name: str, fn, **kwargs):
    """
    Never let one agent's exception take down the whole graph run.
    Returns (result, error_message_or_None).
    """
    try:
        return fn(**kwargs), None
    except Exception as ex:
        return None, f"{agent_name} failed: {ex}"


def call_sub_agents_node(state: OrchestratorState) -> OrchestratorState:
    updates: OrchestratorState = {}
    errors = list(state.get("errors", []))

    for agent_name in state.get("agents_to_call", []):
        spec = AGENT_REGISTRY.get(agent_name)

        if spec is None:
            errors.append(f"Unknown agent requested: '{agent_name}'")
            continue

        kwargs = INPUT_BUILDERS[agent_name](state)
        result, error = _safe_call(spec.display_name, spec.run_fn, **kwargs)

        if error:
            errors.append(error)

        updates[spec.state_key] = result

    updates["errors"] = errors
    return updates
