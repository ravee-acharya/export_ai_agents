"""
Unit tests for orchestrator/query_parser.py's LLM-driven agent
selection ("Planner Agent" upgrade). The priority here is the
validation logic (_validate_agent_selection) -- an LLM can return
malformed, empty, or hallucinated agent names, and this must always
fall back to keyword-based detection rather than trusting bad input.
"""

from orchestrator.query_parser import _validate_agent_selection, parse_query


class _FakeResponse:
    def __init__(self, text):
        self.content = text


class _FakeLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, prompt):
        return _FakeResponse(self.response_text)


def test_validate_accepts_valid_agent_list():
    result = _validate_agent_selection(["demand_signal", "pricing"])
    assert result == ["demand_signal", "pricing"]


def test_validate_rejects_none():
    assert _validate_agent_selection(None) is None


def test_validate_rejects_empty_list():
    assert _validate_agent_selection([]) is None


def test_validate_rejects_non_list():
    assert _validate_agent_selection("demand_signal") is None


def test_validate_rejects_list_with_non_string_items():
    assert _validate_agent_selection(["demand_signal", 123]) is None


def test_validate_rejects_hallucinated_agent_name():
    assert _validate_agent_selection(["demand_signal", "made_up_agent"]) is None


def test_parse_query_uses_llm_selected_agents_when_valid(monkeypatch):
    fake_llm = _FakeLLM(
        '{"sector": "textiles", "target_countries": ["US"], "hs_codes": ["6302"], '
        '"sme_revenue_cr": null, "relevant_agents": ["pricing", "risk"]}'
    )
    monkeypatch.setattr(
        "orchestrator.query_parser.get_llm", lambda provider=None: fake_llm
    )

    result = parse_query("what's the pricing and risk for cotton towels to the US?")
    assert result["agents_to_call"] == ["pricing", "risk"]


def test_parse_query_falls_back_when_llm_agents_invalid(monkeypatch):
    fake_llm = _FakeLLM(
        '{"sector": "textiles", "target_countries": ["US"], "hs_codes": ["6302"], '
        '"sme_revenue_cr": null, "relevant_agents": ["made_up_agent"]}'
    )
    monkeypatch.setattr(
        "orchestrator.query_parser.get_llm", lambda provider=None: fake_llm
    )

    result = parse_query("export cotton towels to the US")

    # Falls back to keyword-based detection, which for a generic query
    # returns the full default agent set -- never crashes on the bad name.
    from orchestrator.registry import default_agents
    assert set(result["agents_to_call"]) == set(default_agents())


def test_parse_query_includes_conversation_context_in_prompt(monkeypatch):
    # Regression test for the bug where follow-up queries lost sector/
    # country context: conversation_context reached the synthesizer but
    # was never passed into parse_query at all, so a follow-up like
    # "what about certification costs?" had no countries to work with.
    captured_prompt = {}

    class _CapturingLLM:
        def invoke(self, prompt):
            captured_prompt["text"] = prompt
            return _FakeResponse(
                '{"sector": "textiles", "target_countries": ["US"], '
                '"hs_codes": ["6302"], "sme_revenue_cr": null}'
            )

    monkeypatch.setattr(
        "orchestrator.query_parser.get_llm", lambda provider=None: _CapturingLLM()
    )

    parse_query(
        "what about the certification costs?",
        conversation_context="Turn 1: asked about cotton towels to US and UAE.",
    )

    assert "cotton towels to US and UAE" in captured_prompt["text"]


def test_parse_query_with_no_context_omits_context_block(monkeypatch):
    captured_prompt = {}

    class _CapturingLLM:
        def invoke(self, prompt):
            captured_prompt["text"] = prompt
            return _FakeResponse(
                '{"sector": "textiles", "target_countries": ["US"], '
                '"hs_codes": ["6302"], "sme_revenue_cr": null}'
            )

    monkeypatch.setattr(
        "orchestrator.query_parser.get_llm", lambda provider=None: _CapturingLLM()
    )

    parse_query("export cotton towels to the US")

    assert "Prior conversation context" not in captured_prompt["text"]
    fake_llm = _FakeLLM(
        '{"sector": "textiles", "target_countries": ["US"], "hs_codes": ["6302"], '
        '"sme_revenue_cr": null}'
    )
    monkeypatch.setattr(
        "orchestrator.query_parser.get_llm", lambda provider=None: fake_llm
    )

    result = parse_query("export cotton towels to the US")

    from orchestrator.registry import default_agents
    assert set(result["agents_to_call"]) == set(default_agents())
