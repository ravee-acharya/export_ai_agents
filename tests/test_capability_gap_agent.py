"""
Unit tests for agents/capability_gap_agent.py.

This is the first LLM-backed (Pattern B) agent, so these tests cover
what the deterministic agents don't need: JSON parsing from an LLM
response, and the fallback behavior when the LLM call or parsing
fails. The fallback path is the most important thing to test here —
an LLM-backed agent has more ways to fail than a lookup-based one, and
it must never crash the graph.
"""

import pytest

from agents.capability_gap_agent import (
    CapabilityGapAgentOutput,
    _gap_score_to_distance,
    run_capability_gap_agent,
)


class _FakeResponse:
    def __init__(self, text):
        self.content = text


class _FakeLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, prompt):
        return _FakeResponse(self.response_text)


class _RaisingLLM:
    def invoke(self, prompt):
        raise RuntimeError("simulated LLM failure")


def test_gap_score_to_distance_mapping():
    assert _gap_score_to_distance(1) == 0.0
    assert _gap_score_to_distance(5) == 1.0
    assert _gap_score_to_distance(3) == 0.5


def test_gap_score_to_distance_clamps_out_of_range():
    assert _gap_score_to_distance(0) == 0.0
    assert _gap_score_to_distance(10) == 1.0


def test_successful_llm_response_parsed_correctly(monkeypatch):
    fake_llm = _FakeLLM(
        '{"gap_score": 2, "missing_requirements": ["OEKO-TEX"], '
        '"upgrade_path": ["Get certified"], "reasoning": "Partial match."}'
    )
    monkeypatch.setattr(
        "agents.capability_gap_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_capability_gap_agent(
        sector="textiles",
        target_countries=["DE"],
        sme_certifications=["ISO 9001"],
        provider="anthropic",
    )

    assert isinstance(output, CapabilityGapAgentOutput)
    assert output.gap_score == 2
    assert output.capability_distance == 0.25
    assert "OEKO-TEX" in output.missing_requirements
    assert output.reasoning == "Partial match."


def test_llm_response_wrapped_in_markdown_fences_still_parses(monkeypatch):
    fake_llm = _FakeLLM(
        '```json\n{"gap_score": 4, "missing_requirements": [], '
        '"upgrade_path": [], "reasoning": "test"}\n```'
    )
    monkeypatch.setattr(
        "agents.capability_gap_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_capability_gap_agent(
        sector="textiles", target_countries=["US"]
    )

    assert output.gap_score == 4
    assert output.capability_distance == 0.75


def test_llm_exception_falls_back_gracefully_not_raises(monkeypatch):
    monkeypatch.setattr(
        "agents.capability_gap_agent.get_llm", lambda provider=None: _RaisingLLM()
    )

    # Must not raise -- this is the core contract for graph safety.
    output = run_capability_gap_agent(
        sector="textiles", target_countries=["US"]
    )

    assert isinstance(output, CapabilityGapAgentOutput)
    assert output.gap_score == 3  # conservative default
    assert output.capability_distance == 0.5
    assert "Assessment unavailable" in output.reasoning


def test_malformed_json_response_falls_back_gracefully(monkeypatch):
    fake_llm = _FakeLLM("this is not json at all, sorry")
    monkeypatch.setattr(
        "agents.capability_gap_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_capability_gap_agent(
        sector="textiles", target_countries=["US"]
    )

    assert output.gap_score == 3
    assert output.capability_distance == 0.5


def test_empty_certifications_still_produces_output(monkeypatch):
    fake_llm = _FakeLLM(
        '{"gap_score": 5, "missing_requirements": ["everything"], '
        '"upgrade_path": [], "reasoning": "no certs on file"}'
    )
    monkeypatch.setattr(
        "agents.capability_gap_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_capability_gap_agent(
        sector="textiles", target_countries=["US"], sme_certifications=None
    )

    assert output.gap_score == 5
