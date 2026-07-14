"""
Unit tests for agents/buyer_discovery_agent.py.

Like test_capability_gap_agent.py, the priority here is the fallback
path -- an LLM-backed agent has more failure modes than a lookup-based
one, and this agent has an additional constraint worth testing
directly: it must never fabricate specific company names, even in its
fallback behavior.
"""

from agents.buyer_discovery_agent import (
    BuyerDiscoveryOutput,
    _FALLBACK_CHANNELS,
    run_buyer_discovery_agent,
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


_VALID_RESPONSE = """
{
  "buyer_personas": [
    {
      "persona_name": "Mid-size home textile distributors",
      "description": "Regional distributors supplying department stores.",
      "typical_order_size": "5,000-20,000 units per order",
      "procurement_notes": "Source via trade fairs and B2B platforms."
    }
  ],
  "recommended_channels": ["Trade fairs", "B2B sourcing platforms"],
  "outreach_tips": ["Prepare a product catalog with certifications listed"],
  "reasoning": "Textiles sector typically sells through distributors."
}
"""


def test_successful_llm_response_parsed_correctly(monkeypatch):
    fake_llm = _FakeLLM(_VALID_RESPONSE)
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_buyer_discovery_agent(
        sector="textiles", target_countries=["US"], provider="anthropic"
    )

    assert isinstance(output, BuyerDiscoveryOutput)
    assert len(output.buyer_personas) == 1
    assert output.buyer_personas[0].persona_name == "Mid-size home textile distributors"
    assert "Trade fairs" in output.recommended_channels
    assert output.outreach_tips


def test_markdown_fenced_response_still_parses(monkeypatch):
    fenced = f"```json\n{_VALID_RESPONSE}\n```"
    fake_llm = _FakeLLM(fenced)
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_buyer_discovery_agent(sector="textiles", target_countries=["US"])
    assert len(output.buyer_personas) == 1


def test_llm_exception_falls_back_without_raising(monkeypatch):
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: _RaisingLLM()
    )

    output = run_buyer_discovery_agent(sector="textiles", target_countries=["US"])

    assert isinstance(output, BuyerDiscoveryOutput)
    assert output.buyer_personas == []
    assert output.recommended_channels == _FALLBACK_CHANNELS
    assert "unavailable" in output.reasoning.lower()


def test_malformed_json_falls_back_without_raising(monkeypatch):
    fake_llm = _FakeLLM("not json at all")
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_buyer_discovery_agent(sector="textiles", target_countries=["US"])

    assert output.buyer_personas == []
    assert output.recommended_channels == _FALLBACK_CHANNELS


def test_fallback_channels_never_name_specific_companies():
    # The one hard constraint for this agent: even its safety-net
    # fallback must not look like it's naming real buyer companies.
    # (It's fine to name well-known *platforms* like Alibaba/IndiaMART
    # since those are general channels, not fabricated buyer leads.)
    suspicious_terms = ["walmart", "target corp", "ikea", "costco"]
    channels_text = " ".join(_FALLBACK_CHANNELS).lower()
    for term in suspicious_terms:
        assert term not in channels_text


def test_prompt_includes_no_fabrication_constraint(monkeypatch):
    captured_prompt = {}

    class _CapturingLLM:
        def invoke(self, prompt):
            captured_prompt["text"] = prompt
            return _FakeResponse(_VALID_RESPONSE)

    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm",
        lambda provider=None: _CapturingLLM(),
    )

    run_buyer_discovery_agent(sector="textiles", target_countries=["US"])

    prompt_lower = captured_prompt["text"].lower()
    assert "do not name any specific real company" in prompt_lower


def test_missing_optional_fields_default_sensibly(monkeypatch):
    minimal_response = """
    {
      "buyer_personas": [
        {"persona_name": "Test persona"}
      ]
    }
    """
    fake_llm = _FakeLLM(minimal_response)
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_buyer_discovery_agent(sector="textiles", target_countries=["US"])

    assert output.buyer_personas[0].persona_name == "Test persona"
    assert output.buyer_personas[0].description == ""
    # recommended_channels falls back when the key is entirely absent
    assert output.recommended_channels == _FALLBACK_CHANNELS


def test_empty_target_countries_still_produces_output(monkeypatch):
    fake_llm = _FakeLLM(_VALID_RESPONSE)
    monkeypatch.setattr(
        "agents.buyer_discovery_agent.get_llm", lambda provider=None: fake_llm
    )

    output = run_buyer_discovery_agent(sector="textiles", target_countries=[])
    assert isinstance(output, BuyerDiscoveryOutput)
