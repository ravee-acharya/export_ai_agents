"""
Unit tests for orchestrator/dispatcher.py.

Monkeypatches orchestrator.dispatcher.AGENT_REGISTRY and
INPUT_BUILDERS directly (the names dispatcher.py imported them under)
so these tests verify the dispatch/error-handling logic in isolation,
without depending on the real agents or their side effects.
"""

from dataclasses import dataclass

import pytest

from orchestrator.dispatcher import _safe_call, call_sub_agents_node
from orchestrator.registry import AgentSpec


@dataclass
class _FakeOutput:
    value: str


def _make_registry(specs: dict):
    return specs


def test_safe_call_returns_result_on_success():
    result, error = _safe_call("Test Agent", lambda x: x * 2, x=5)
    assert result == 10
    assert error is None


def test_safe_call_catches_exception_and_returns_error_message():
    def _raises(**kwargs):
        raise ValueError("boom")

    result, error = _safe_call("Test Agent", _raises)
    assert result is None
    assert "Test Agent failed" in error
    assert "boom" in error


def test_dispatch_calls_run_fn_and_stores_at_state_key(monkeypatch):
    spec = AgentSpec(
        name="fake",
        display_name="Fake Agent",
        run_fn=lambda sector: _FakeOutput(value=sector),
        state_key="fake_output",
    )
    monkeypatch.setattr("orchestrator.dispatcher.AGENT_REGISTRY", {"fake": spec})
    monkeypatch.setattr(
        "orchestrator.dispatcher.INPUT_BUILDERS",
        {"fake": lambda state: {"sector": state["sector"]}},
    )

    state = {"sector": "textiles", "agents_to_call": ["fake"]}
    result = call_sub_agents_node(state)

    assert result["fake_output"].value == "textiles"
    assert result["errors"] == []


def test_dispatch_unknown_agent_name_appends_error_not_raises(monkeypatch):
    monkeypatch.setattr("orchestrator.dispatcher.AGENT_REGISTRY", {})
    monkeypatch.setattr("orchestrator.dispatcher.INPUT_BUILDERS", {})

    state = {"agents_to_call": ["nonexistent"]}
    result = call_sub_agents_node(state)

    assert len(result["errors"]) == 1
    assert "Unknown agent" in result["errors"][0]
    assert "nonexistent" in result["errors"][0]


def test_dispatch_agent_exception_is_caught_and_output_is_none(monkeypatch):
    def _raises(sector):
        raise RuntimeError("agent exploded")

    spec = AgentSpec(
        name="fake",
        display_name="Fake Agent",
        run_fn=_raises,
        state_key="fake_output",
    )
    monkeypatch.setattr("orchestrator.dispatcher.AGENT_REGISTRY", {"fake": spec})
    monkeypatch.setattr(
        "orchestrator.dispatcher.INPUT_BUILDERS",
        {"fake": lambda state: {"sector": state["sector"]}},
    )

    state = {"sector": "textiles", "agents_to_call": ["fake"]}
    result = call_sub_agents_node(state)

    assert result["fake_output"] is None
    assert len(result["errors"]) == 1
    assert "Fake Agent failed" in result["errors"][0]


def test_dispatch_preserves_existing_errors_from_state(monkeypatch):
    spec = AgentSpec(
        name="fake",
        display_name="Fake Agent",
        run_fn=lambda sector: _FakeOutput(value=sector),
        state_key="fake_output",
    )
    monkeypatch.setattr("orchestrator.dispatcher.AGENT_REGISTRY", {"fake": spec})
    monkeypatch.setattr(
        "orchestrator.dispatcher.INPUT_BUILDERS",
        {"fake": lambda state: {"sector": state["sector"]}},
    )

    state = {
        "sector": "textiles",
        "agents_to_call": ["fake"],
        "errors": ["pre-existing error"],
    }
    result = call_sub_agents_node(state)

    assert "pre-existing error" in result["errors"]
    assert len(result["errors"]) == 1  # no new errors added


def test_dispatch_runs_multiple_agents_independently(monkeypatch):
    good_spec = AgentSpec(
        name="good",
        display_name="Good Agent",
        run_fn=lambda sector: _FakeOutput(value=sector),
        state_key="good_output",
    )

    def _bad_fn(sector):
        raise RuntimeError("bad agent failed")

    bad_spec = AgentSpec(
        name="bad",
        display_name="Bad Agent",
        run_fn=_bad_fn,
        state_key="bad_output",
    )

    monkeypatch.setattr(
        "orchestrator.dispatcher.AGENT_REGISTRY",
        {"good": good_spec, "bad": bad_spec},
    )
    monkeypatch.setattr(
        "orchestrator.dispatcher.INPUT_BUILDERS",
        {
            "good": lambda state: {"sector": state["sector"]},
            "bad": lambda state: {"sector": state["sector"]},
        },
    )

    state = {"sector": "textiles", "agents_to_call": ["good", "bad"]}
    result = call_sub_agents_node(state)

    # One agent's failure shouldn't stop the other from running.
    assert result["good_output"].value == "textiles"
    assert result["bad_output"] is None
    assert len(result["errors"]) == 1


def test_dispatch_empty_agents_to_call_returns_no_outputs(monkeypatch):
    monkeypatch.setattr("orchestrator.dispatcher.AGENT_REGISTRY", {})
    monkeypatch.setattr("orchestrator.dispatcher.INPUT_BUILDERS", {})

    state = {"agents_to_call": []}
    result = call_sub_agents_node(state)

    assert result["errors"] == []
    assert len(result) == 1  # only "errors" key present
