"""
Tests for orchestrator/dispatcher.py — Sprint 6b async parallel execution.

Key test: agents must run CONCURRENTLY, not sequentially. We verify this
by giving each mock agent a sleep delay and checking that total wall-clock
time is ~1× one agent's delay, not N× all agents' delays.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.dispatcher import (
    MAX_WORKERS,
    _run_agents_concurrently,
    _safe_call,
    call_sub_agents_node,
)


# ------------------------------------------------------------------
# _safe_call unit tests
# ------------------------------------------------------------------

def test_safe_call_returns_result_on_success():
    result, error = _safe_call("test_agent", lambda x: x * 2, x=5)
    assert result == 10
    assert error is None


def test_safe_call_returns_error_message_on_exception():
    def _boom():
        raise ValueError("something went wrong")
    result, error = _safe_call("test_agent", _boom)
    assert result is None
    assert "test_agent failed" in error
    assert "something went wrong" in error


def test_safe_call_captures_any_exception_type():
    def _runtime_error():
        raise RuntimeError("runtime!")
    result, error = _safe_call("a", _runtime_error)
    assert error is not None


# ------------------------------------------------------------------
# Concurrency verification — THE key Sprint 6b test
# ------------------------------------------------------------------

def _make_slow_agent(delay: float, return_value):
    """Returns a function that sleeps for `delay` seconds then returns a value."""
    def _agent(**kwargs):
        time.sleep(delay)
        return return_value
    return _agent


def test_agents_run_concurrently_not_sequentially():
    """
    3 agents each take 0.3s. Sequential would take ~0.9s.
    Concurrent should take ~0.3s (plus overhead).
    We allow up to 0.65s to account for CI variance.
    """
    from dataclasses import dataclass

    @dataclass
    class FakeOutput:
        value: str

    fake_registry = {
        "agent_a": MagicMock(
            display_name="Agent A",
            run_fn=_make_slow_agent(0.3, FakeOutput("a")),
            state_key="output_a",
        ),
        "agent_b": MagicMock(
            display_name="Agent B",
            run_fn=_make_slow_agent(0.3, FakeOutput("b")),
            state_key="output_b",
        ),
        "agent_c": MagicMock(
            display_name="Agent C",
            run_fn=_make_slow_agent(0.3, FakeOutput("c")),
            state_key="output_c",
        ),
    }
    fake_builders = {
        "agent_a": lambda state: {},
        "agent_b": lambda state: {},
        "agent_c": lambda state: {},
    }

    state = {
        "agents_to_call": ["agent_a", "agent_b", "agent_c"],
        "sector": "textiles",
        "target_countries": ["US"],
        "errors": [],
    }

    with patch("orchestrator.dispatcher.AGENT_REGISTRY", fake_registry), \
         patch("orchestrator.dispatcher.INPUT_BUILDERS", fake_builders):

        start = time.monotonic()
        result = call_sub_agents_node(state)
        elapsed = time.monotonic() - start

    # Correctness
    assert result["output_a"].value == "a"
    assert result["output_b"].value == "b"
    assert result["output_c"].value == "c"
    assert result["errors"] == []

    # Concurrency: must be faster than sequential (0.9s)
    assert elapsed < 0.65, (
        f"Agents appear to be running sequentially: took {elapsed:.2f}s "
        f"(expected < 0.65s for 3 concurrent 0.3s agents)"
    )
    print(f"\nConcurrency verified: 3×0.3s agents completed in {elapsed:.2f}s")


def test_one_failing_agent_does_not_block_others():
    """
    If agent_b fails, agent_a and agent_c must still complete and
    their results must be in the state.
    """
    from dataclasses import dataclass

    @dataclass
    class FakeOutput:
        value: str

    def _failing_agent(**kwargs):
        raise RuntimeError("I always fail")

    fake_registry = {
        "agent_a": MagicMock(
            display_name="Agent A",
            run_fn=lambda **kw: FakeOutput("a"),
            state_key="output_a",
        ),
        "agent_b": MagicMock(
            display_name="Agent B",
            run_fn=_failing_agent,
            state_key="output_b",
        ),
        "agent_c": MagicMock(
            display_name="Agent C",
            run_fn=lambda **kw: FakeOutput("c"),
            state_key="output_c",
        ),
    }
    fake_builders = {k: lambda state: {} for k in ["agent_a", "agent_b", "agent_c"]}

    state = {
        "agents_to_call": ["agent_a", "agent_b", "agent_c"],
        "errors": [],
        "sector": "textiles",
        "target_countries": ["US"],
    }

    with patch("orchestrator.dispatcher.AGENT_REGISTRY", fake_registry), \
         patch("orchestrator.dispatcher.INPUT_BUILDERS", fake_builders):
        result = call_sub_agents_node(state)

    assert result["output_a"].value == "a"
    assert result["output_b"] is None         # failed agent returns None
    assert result["output_c"].value == "c"
    assert len(result["errors"]) == 1
    assert "Agent B failed" in result["errors"][0]


def test_unknown_agent_adds_error_without_crashing():
    fake_registry = {}
    fake_builders = {}
    state = {
        "agents_to_call": ["nonexistent_agent"],
        "errors": [],
        "sector": "textiles",
        "target_countries": ["US"],
    }
    with patch("orchestrator.dispatcher.AGENT_REGISTRY", fake_registry), \
         patch("orchestrator.dispatcher.INPUT_BUILDERS", fake_builders):
        result = call_sub_agents_node(state)

    assert any("nonexistent_agent" in e for e in result["errors"])


def test_empty_agents_list_returns_empty_updates():
    state = {"agents_to_call": [], "errors": [], "sector": "textiles", "target_countries": []}
    result = call_sub_agents_node(state)
    assert result["errors"] == []


def test_existing_errors_preserved():
    """Errors from earlier nodes (e.g. planner) must not be wiped."""
    state = {
        "agents_to_call": [],
        "errors": ["prior error from planner"],
        "sector": "textiles",
        "target_countries": [],
    }
    result = call_sub_agents_node(state)
    assert "prior error from planner" in result["errors"]


def test_max_workers_is_reasonable():
    assert 1 <= MAX_WORKERS <= 20
