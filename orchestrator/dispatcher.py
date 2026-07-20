"""
Dispatcher — executes sub-agents concurrently using a thread pool.

Sprint 6b upgrade: agents now run in parallel via asyncio + ThreadPoolExecutor
instead of sequentially. Independent agents (e.g. Pricing and Risk) no longer
wait for each other.

Wall-clock time improvement:
  Before (sequential): N agents × ~2s each = ~24s for 12 agents
  After  (concurrent): max(slowest agent) = ~3-4s regardless of count

Design decisions:
  1. ThreadPoolExecutor (not ProcessPoolExecutor) — agents share in-memory
     mock data and are I/O-bound (LLM calls), not CPU-bound. Threads are
     the right tool.
  2. asyncio.gather with return_exceptions=True — one slow/failing agent
     never blocks or kills others.
  3. The graph node itself (call_sub_agents_node) is synchronous — LangGraph
     calls it normally. We use asyncio.run() to drive the async work inside
     it. This means zero changes to graph.py or any other orchestrator file.
  4. If an event loop is already running (e.g. inside FastAPI's async context
     from Sprint 6a), we use run_in_executor to avoid "cannot run nested
     event loop" errors.
  5. MAX_WORKERS is capped at 12 (one per agent). In production, tune this
     based on how many LLM API connections you want open simultaneously.
"""

import asyncio
import concurrent.futures
from typing import Any

from orchestrator.registry import AGENT_REGISTRY, INPUT_BUILDERS
from orchestrator.state import OrchestratorState

MAX_WORKERS = 12


def _safe_call(agent_name: str, fn, **kwargs) -> tuple[Any, str | None]:
    """
    Run one agent. Never lets an exception propagate — returns
    (result, None) on success or (None, error_message) on failure.
    """
    try:
        return fn(**kwargs), None
    except Exception as ex:
        return None, f"{agent_name} failed: {ex}"


async def _run_agents_concurrently(
    agents_to_call: list[str],
    state: OrchestratorState,
) -> tuple[dict, list[str]]:
    """
    Run all requested agents concurrently in a thread pool.
    Returns (updates_dict, errors_list).
    """
    loop = asyncio.get_event_loop()
    errors: list[str] = []
    updates: dict = {}

    # Build the list of (agent_name, fn, kwargs) to run
    tasks = []
    for agent_name in agents_to_call:
        spec = AGENT_REGISTRY.get(agent_name)
        if spec is None:
            errors.append(f"Unknown agent requested: '{agent_name}'")
            continue
        kwargs = INPUT_BUILDERS[agent_name](state)
        tasks.append((agent_name, spec))

    if not tasks:
        return updates, errors

    # Submit all agents to the thread pool simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            agent_name: loop.run_in_executor(
                executor,
                lambda spec=spec, kw=INPUT_BUILDERS[agent_name](state):
                    _safe_call(spec.display_name, spec.run_fn, **kw),
            )
            for agent_name, spec in tasks
        }

        # Gather all results — return_exceptions=True means one failure
        # doesn't cancel the others
        results = await asyncio.gather(*futures.values(), return_exceptions=True)

    for (agent_name, spec), result in zip(tasks, results):
        if isinstance(result, Exception):
            errors.append(f"{agent_name} failed: {result}")
            updates[spec.state_key] = None
        else:
            output, error = result
            if error:
                errors.append(error)
            updates[spec.state_key] = output

    return updates, errors


def call_sub_agents_node(state: OrchestratorState) -> OrchestratorState:
    """
    LangGraph node — synchronous entry point that drives async execution.
    Called by the graph exactly as before; no graph.py changes needed.
    """
    existing_errors = list(state.get("errors", []))
    agents_to_call = state.get("agents_to_call", [])

    try:
        # Check if there's already a running event loop (e.g. inside FastAPI)
        loop = asyncio.get_running_loop()
        # If we're inside an async context, run in a thread to avoid
        # "cannot run nested event loop"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                _run_agents_concurrently(agents_to_call, state),
            )
            updates, new_errors = future.result()
    except RuntimeError:
        # No running loop — we're in a sync context (normal Streamlit/CLI use)
        updates, new_errors = asyncio.run(
            _run_agents_concurrently(agents_to_call, state)
        )

    updates["errors"] = existing_errors + new_errors
    return updates
