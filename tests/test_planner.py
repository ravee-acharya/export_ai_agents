"""
Unit tests for orchestrator/planner.py.

Monkeypatches parse_query (query-parsing/LLM path) so these tests
verify the planner's own branching logic — structured vs. query input,
defaults, and error handling — without depending on a real LLM call.
"""

from orchestrator.planner import planner_node


def test_structured_input_path_used_when_sector_and_countries_present():
    state = {
        "sector": "textiles",
        "hs_codes": ["6302"],
        "target_countries": ["US"],
        "sme_revenue_cr": 40,
        "has_udyam_registration": True,
    }

    result = planner_node(state, provider="anthropic")

    assert result["sector"] == "textiles"
    assert result["hs_codes"] == ["6302"]
    assert result["target_countries"] == ["US"]
    assert result["sme_revenue_cr"] == 40
    assert result["provider"] == "anthropic"
    assert "agents_to_call" in result


def test_structured_input_defaults_certifications_to_empty_list():
    state = {"sector": "textiles", "hs_codes": ["6302"], "target_countries": ["US"]}
    result = planner_node(state)
    assert result["sme_certifications"] == []


def test_structured_input_defaults_udyam_to_true():
    state = {"sector": "textiles", "hs_codes": ["6302"], "target_countries": ["US"]}
    result = planner_node(state)
    assert result["has_udyam_registration"] is True


def test_structured_input_preserves_explicit_certifications():
    state = {
        "sector": "textiles",
        "hs_codes": ["6302"],
        "target_countries": ["US"],
        "sme_certifications": ["ISO 9001"],
    }
    result = planner_node(state)
    assert result["sme_certifications"] == ["ISO 9001"]


def test_empty_query_and_no_structured_input_returns_error():
    result = planner_node({"query": ""})
    assert result["errors"] == ["No query provided."]
    assert result["agents_to_call"] == []


def test_missing_query_key_entirely_returns_error():
    result = planner_node({})
    assert result["errors"] == ["No query provided."]
    assert result["agents_to_call"] == []


def test_query_path_calls_parse_query_and_maps_fields(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.planner.parse_query",
        lambda query, provider=None, conversation_context="": {
            "sector": "textiles",
            "hs_codes": ["6302"],
            "target_countries": ["US"],
            "sme_revenue_cr": 40,
            "has_udyam_registration": True,
            "sme_certifications": [],
            "agents_to_call": ["demand_signal"],
        },
    )

    result = planner_node({"query": "export cotton towels to the US"}, provider="gemini")

    assert result["sector"] == "textiles"
    assert result["target_countries"] == ["US"]
    assert result["provider"] == "gemini"
    assert result["agents_to_call"] == ["demand_signal"]


def test_query_path_passes_conversation_context_to_parse_query(monkeypatch):
    # This is the exact bug that caused follow-up questions to lose
    # sector/country context: parse_query wasn't being given the
    # conversation_context at all. Guard against regressing it.
    captured = {}

    def _capturing_parse_query(query, provider=None, conversation_context=""):
        captured["conversation_context"] = conversation_context
        return {
            "sector": "textiles",
            "hs_codes": ["6302"],
            "target_countries": ["US"],
        }

    monkeypatch.setattr("orchestrator.planner.parse_query", _capturing_parse_query)

    planner_node(
        {
            "query": "what about the certification costs?",
            "conversation_context": "Turn 1: asked about cotton towels to US and UAE.",
        }
    )

    assert captured["conversation_context"] == "Turn 1: asked about cotton towels to US and UAE."


def test_query_path_falls_back_to_default_agents_when_not_specified(monkeypatch):
    monkeypatch.setattr(
        "orchestrator.planner.parse_query",
        lambda query, provider=None, conversation_context="": {
            "sector": "textiles",
            "hs_codes": ["6302"],
            "target_countries": ["US"],
            # no "agents_to_call" key at all
        },
    )

    result = planner_node({"query": "export cotton towels"})

    from orchestrator.registry import default_agents
    assert set(result["agents_to_call"]) == set(default_agents())


def test_query_parsing_exception_caught_not_raised(monkeypatch):
    def _raises(query, provider=None, conversation_context=""):
        raise RuntimeError("LLM call failed")

    monkeypatch.setattr("orchestrator.planner.parse_query", _raises)

    result = planner_node({"query": "export cotton towels"})

    assert result["agents_to_call"] == []
    assert len(result["errors"]) == 1
    assert "Query parsing failed" in result["errors"][0]
    assert "LLM call failed" in result["errors"][0]


def test_query_stripped_of_whitespace_before_emptiness_check():
    result = planner_node({"query": "   "})
    assert result["errors"] == ["No query provided."]


def test_structured_path_takes_priority_over_query_when_both_present(monkeypatch):
    # If sector + target_countries are present, the query should be
    # ignored entirely -- parse_query must not even be called.
    called = {"was_called": False}

    def _tracking_parse_query(query, provider=None, conversation_context=""):
        called["was_called"] = True
        return {}

    monkeypatch.setattr("orchestrator.planner.parse_query", _tracking_parse_query)

    state = {
        "query": "this should be ignored",
        "sector": "textiles",
        "hs_codes": ["6302"],
        "target_countries": ["US"],
    }
    result = planner_node(state)

    assert called["was_called"] is False
    assert result["sector"] == "textiles"
