"""
Regression tests for the "which markets should I target?" bug.

Real bug: when a user asks a market-discovery question ("which are the
top 3 markets for me?") without naming any country, parse_query
correctly detects sector/HS codes but target_countries comes back
empty. Every downstream agent (pricing, risk, logistics, demand) needs
target_countries to iterate over, so all of them produced nothing,
and the whole query dead-ended with "No data was generated" -- even
though sector detection worked perfectly.

Fix: orchestrator/planner.py substitutes a default candidate market
list when parse_query returns no countries, and sets
markets_auto_selected=True so the synthesizer can tell the person
plainly that markets were chosen for them.

A second bug was caught while fixing the first: LangGraph's
StateGraph only propagates state keys that are declared in the
OrchestratorState TypedDict schema. markets_auto_selected was
originally returned by planner_node without being added to the
schema, so LangGraph silently dropped it when merging node outputs --
proven by testing planner_node in isolation (flag present) versus the
full graph (flag missing) before the schema fix.
"""

from unittest.mock import patch

from orchestrator.planner import planner_node, DEFAULT_CANDIDATE_MARKETS


def _fake_parse_query_no_countries(query, provider=None, conversation_context=""):
    return {
        "sector": "ceramics",
        "hs_codes": ["6907", "6908", "6910"],
        "target_countries": [],
        "sme_revenue_cr": None,
        "agents_to_call": ["demand_signal"],
    }


def _fake_parse_query_with_countries(query, provider=None, conversation_context=""):
    return {
        "sector": "ceramics",
        "hs_codes": ["6907"],
        "target_countries": ["US", "AE"],
        "sme_revenue_cr": None,
        "agents_to_call": ["demand_signal"],
    }


def test_planner_defaults_countries_when_none_named():
    with patch("orchestrator.planner.parse_query", _fake_parse_query_no_countries):
        result = planner_node({"query": "which are the top 3 markets for me?"})

    assert result["target_countries"] == DEFAULT_CANDIDATE_MARKETS
    assert result["target_countries"], "must never be empty after planning"
    assert result["markets_auto_selected"] is True


def test_planner_leaves_countries_alone_when_explicitly_named():
    with patch("orchestrator.planner.parse_query", _fake_parse_query_with_countries):
        result = planner_node({"query": "export to US and UAE"})

    assert result["target_countries"] == ["US", "AE"]
    assert result["markets_auto_selected"] is False


def test_default_candidate_markets_have_real_data_coverage():
    """
    The default list is only useful if every agent can actually produce
    data for these countries. Verify against the real data sources
    rather than assuming the list stays in sync.
    """
    from data_sources.risk_data import _RISK_DATA
    from data_sources.logistics_data import _LOGISTICS_DATA
    from data_sources.comtrade_api import _PARTNER_CODES

    for country in DEFAULT_CANDIDATE_MARKETS:
        assert country in _RISK_DATA, f"{country} missing from risk_data"
        assert country in _LOGISTICS_DATA, f"{country} missing from logistics_data"
        assert country in _PARTNER_CODES, f"{country} missing from comtrade partner codes"


def test_structured_path_unaffected_by_default_countries_logic():
    """The structured-input path (sidebar form) must be untouched --
    it always has explicit countries already, so markets_auto_selected
    should not even be set."""
    state = {
        "sector": "ceramics",
        "target_countries": ["US"],
        "hs_codes": ["6907"],
    }
    result = planner_node(state)
    assert result["target_countries"] == ["US"]
    assert "markets_auto_selected" not in result


def test_markets_auto_selected_declared_in_state_schema():
    """
    Regression test for the LangGraph state-propagation bug: a state
    key returned by a node but not declared in OrchestratorState is
    silently dropped when the graph merges node outputs. This checks
    the field is actually declared, not just present in planner_node's
    local return dict.
    """
    from orchestrator.state import OrchestratorState
    assert "markets_auto_selected" in OrchestratorState.__annotations__


def test_synthesizer_includes_auto_select_explanation_in_prompt():
    """
    When markets_auto_selected is True, the synthesizer must tell the
    person plainly that markets were chosen for them -- verified by
    checking the actual prompt sent to the LLM, not by parsing the
    (mocked) response text.
    """
    from unittest.mock import MagicMock
    from orchestrator.synthesizer import synthesize_node

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = MagicMock(content="stub summary")

    with patch("orchestrator.synthesizer.get_llm", return_value=fake_llm):
        state = {
            "opportunity_scores": [
                {"hs_code": "6907", "destination_country": "US", "score": 50.0,
                 "score_breakdown": {}, "note": ""},
            ],
            "target_countries": ["US", "DE", "AE", "GB", "SG"],
            "markets_auto_selected": True,
        }
        synthesize_node(state)

    prompt_sent = fake_llm.invoke.call_args[0][0]
    assert "did not name specific target countries" in prompt_sent
    assert "US, DE, AE, GB, SG" in prompt_sent


def test_synthesizer_omits_auto_select_note_when_countries_were_named():
    from unittest.mock import MagicMock
    from orchestrator.synthesizer import synthesize_node

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = MagicMock(content="stub summary")

    with patch("orchestrator.synthesizer.get_llm", return_value=fake_llm):
        state = {
            "opportunity_scores": [
                {"hs_code": "6907", "destination_country": "US", "score": 50.0,
                 "score_breakdown": {}, "note": ""},
            ],
            "target_countries": ["US"],
            "markets_auto_selected": False,
        }
        synthesize_node(state)

    prompt_sent = fake_llm.invoke.call_args[0][0]
    assert "did not name specific target countries" not in prompt_sent
