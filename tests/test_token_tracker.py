"""Tests for orchestrator/token_tracker.py"""
import pytest
from orchestrator.token_tracker import (
    TokenTracker, AgentTokenUsage, QueryTokenSummary, record_usage, token_tracker
)


def _fake_langchain_response(input_tokens, output_tokens, model="openrouter/auto"):
    class FakeResponse:
        content = "test response"
        response_metadata = {
            "token_usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
            },
            "model_name": model,
        }
    return FakeResponse()


def _fake_gemini_response(input_tokens, output_tokens):
    class FakeResponse:
        content = "test response"
        usage_metadata = {
            "promptTokenCount": input_tokens,
            "candidatesTokenCount": output_tokens,
        }
    return FakeResponse()


def _fake_response_no_usage():
    class FakeResponse:
        content = "hello world test response content"
    return FakeResponse()


def test_record_langchain_response():
    tracker = TokenTracker()
    tracker.reset(model="openrouter/auto")
    tracker.record("test_agent", _fake_langchain_response(100, 50))
    summary = tracker.get_summary()
    assert summary.total_input_tokens == 100
    assert summary.total_output_tokens == 50
    assert summary.total_tokens == 150


def test_record_gemini_response():
    tracker = TokenTracker()
    tracker.reset(model="gemini-2.5-flash")
    tracker.record("test_agent", _fake_gemini_response(200, 80))
    summary = tracker.get_summary()
    assert summary.total_input_tokens == 200
    assert summary.total_output_tokens == 80


def test_fallback_estimates_from_content_length():
    tracker = TokenTracker()
    tracker.reset()
    tracker.record("test_agent", _fake_response_no_usage())
    summary = tracker.get_summary()
    # Content "hello world test response content" is ~33 chars → ~8 tokens
    assert summary.total_output_tokens > 0


def test_multiple_agents_accumulate():
    tracker = TokenTracker()
    tracker.reset(model="openrouter/auto")
    tracker.record("agent_a", _fake_langchain_response(100, 50))
    tracker.record("agent_b", _fake_langchain_response(200, 80))
    tracker.record("agent_c", _fake_langchain_response(150, 60))
    summary = tracker.get_summary()
    assert summary.total_input_tokens == 450
    assert summary.total_output_tokens == 190
    assert len(summary.per_agent) == 3


def test_reset_clears_previous_data():
    tracker = TokenTracker()
    tracker.reset(model="openrouter/auto")
    tracker.record("agent_a", _fake_langchain_response(500, 200))
    tracker.reset(model="gemini-2.5-flash")
    summary = tracker.get_summary()
    assert summary.total_tokens == 0
    assert len(summary.per_agent) == 0


def test_cost_zero_for_free_models():
    tracker = TokenTracker()
    tracker.reset(model="openrouter/auto")
    tracker.record("agent_a", _fake_langchain_response(1000, 500, "openrouter/auto"))
    summary = tracker.get_summary()
    assert summary.total_cost_usd == 0.0


def test_cost_nonzero_for_paid_model():
    tracker = TokenTracker()
    tracker.reset(model="claude-sonnet-4-6")
    tracker.record("agent_a", _fake_langchain_response(1000, 500, "claude-sonnet-4-6"))
    summary = tracker.get_summary()
    assert summary.total_cost_usd > 0.0


def test_to_dict_has_required_fields():
    tracker = TokenTracker()
    tracker.reset(model="openrouter/auto")
    tracker.record("synthesizer", _fake_langchain_response(300, 150))
    d = tracker.get_summary().to_dict()
    assert "model" in d
    assert "total_input_tokens" in d
    assert "total_output_tokens" in d
    assert "total_tokens" in d
    assert "total_cost_usd" in d
    assert "per_agent" in d
    assert d["per_agent"][0]["agent"] == "synthesizer"


def test_per_agent_sorted_by_total_tokens_descending():
    tracker = TokenTracker()
    tracker.reset()
    tracker.record("small_agent", _fake_langchain_response(10, 5))
    tracker.record("large_agent", _fake_langchain_response(500, 200))
    tracker.record("medium_agent", _fake_langchain_response(100, 50))
    d = tracker.get_summary().to_dict()
    totals = [a["total_tokens"] for a in d["per_agent"]]
    assert totals == sorted(totals, reverse=True)


def test_never_crashes_on_bad_response():
    tracker = TokenTracker()
    tracker.reset()
    tracker.record("agent_a", None)          # None response
    tracker.record("agent_b", "raw string")  # string response
    tracker.record("agent_c", 42)            # integer response
    # Should not raise, just record 0s
    summary = tracker.get_summary()
    assert len(summary.per_agent) == 3
