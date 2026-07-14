"""
Unit tests for agents/rag_agent.py.

Monkeypatches retrieve_snippets so these tests verify the agent's own
query-combination and empty-input handling, not the specific mock
knowledge base content.
"""

from agents.rag_agent import RAGAgentOutput, run_rag_agent


def test_returns_snippets_from_retrieval(monkeypatch):
    fake_snippets = ["snippet_a", "snippet_b"]
    monkeypatch.setattr(
        "agents.rag_agent.retrieve_snippets",
        lambda query, top_k=3: fake_snippets,
    )

    output = run_rag_agent(query="tell me about FTA rules", sector="textiles")

    assert isinstance(output, RAGAgentOutput)
    assert output.snippets == fake_snippets


def test_combines_query_and_sector_for_retrieval(monkeypatch):
    captured = {}

    def _fake_retrieve(query, top_k=3):
        captured["query"] = query
        return []

    monkeypatch.setattr("agents.rag_agent.retrieve_snippets", _fake_retrieve)

    run_rag_agent(query="FTA rules", sector="textiles")

    assert "FTA rules" in captured["query"]
    assert "textiles" in captured["query"]


def test_empty_query_and_sector_returns_no_snippets_without_calling_retrieval(monkeypatch):
    called = {"was_called": False}

    def _fake_retrieve(query, top_k=3):
        called["was_called"] = True
        return []

    monkeypatch.setattr("agents.rag_agent.retrieve_snippets", _fake_retrieve)

    output = run_rag_agent(query="", sector=None)

    assert output.snippets == []
    assert called["was_called"] is False


def test_none_query_treated_as_empty_string():
    output = run_rag_agent(query=None, sector=None)
    assert output.query == ""
    assert output.snippets == []


def test_top_k_passed_through(monkeypatch):
    captured = {}

    def _fake_retrieve(query, top_k=3):
        captured["top_k"] = top_k
        return []

    monkeypatch.setattr("agents.rag_agent.retrieve_snippets", _fake_retrieve)

    run_rag_agent(query="test", sector="textiles", top_k=5)
    assert captured["top_k"] == 5
