"""
Unit tests for data_sources/knowledge_base.py's retrieve_snippets --
the actual (mock) retrieval logic, tested directly against the real
corpus since it's small and static.
"""

from data_sources.knowledge_base import retrieve_snippets


def test_retrieval_finds_relevant_snippet_by_keyword():
    results = retrieve_snippets("what is anti-dumping duty")
    titles = [r.title for r in results]
    assert "Anti-Dumping Duty Basics" in titles


def test_retrieval_respects_top_k():
    results = retrieve_snippets("tariff duty scheme risk", top_k=2)
    assert len(results) <= 2


def test_retrieval_returns_empty_for_irrelevant_query():
    results = retrieve_snippets("recipe for chocolate cake")
    assert results == []


def test_retrieval_is_case_insensitive():
    results_lower = retrieve_snippets("udyam registration")
    results_upper = retrieve_snippets("UDYAM REGISTRATION")
    assert len(results_lower) > 0
    assert [r.title for r in results_lower] == [r.title for r in results_upper]
