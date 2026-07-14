"""
Unit tests for orchestrator/registry.py — the agent selection logic
that used to be hardcoded/scattered across main_agent.py and
query_parser.py before the refactor.
"""

from orchestrator.registry import (
    AGENT_REGISTRY,
    default_agents,
    detect_agents_from_query,
)


def test_all_twelve_agents_registered():
    assert set(AGENT_REGISTRY.keys()) == {
        "demand_signal",
        "scheme_compliance",
        "pricing",
        "capability_gap",
        "logistics",
        "risk",
        "competitor",
        "buyer_discovery",
        "fta",
        "document_intelligence",
        "certification",
        "rag",
    }


def test_default_agents_includes_all_default_true_specs():
    defaults = default_agents()
    for name, spec in AGENT_REGISTRY.items():
        if spec.default:
            assert name in defaults
        else:
            assert name not in defaults


def test_scheme_only_query_is_exclusive():
    agents = detect_agents_from_query("what government schemes are available?")
    assert agents == ["scheme_compliance"]


def test_generic_export_query_returns_default_set():
    agents = detect_agents_from_query("export cotton towels to germany")
    assert set(agents) == set(default_agents())


def test_pricing_keyword_does_not_override_defaults():
    # Pricing isn't marked exclusive, so a pricing-flavored query
    # should still run the full default set, not pricing alone.
    agents = detect_agents_from_query("what price should I set for my product?")
    assert set(agents) == set(default_agents())


def test_scheme_keywords_are_case_insensitive():
    agents = detect_agents_from_query("Tell me about SUBSIDY programs")
    assert agents == ["scheme_compliance"]


def test_unknown_agent_name_lookup_returns_none():
    assert AGENT_REGISTRY.get("nonexistent_agent") is None
