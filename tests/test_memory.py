"""
Unit tests for orchestrator/memory.py.
"""

from orchestrator.memory import ConversationMemory


def test_add_and_retrieve_turn():
    memory = ConversationMemory()
    memory.add_turn(
        "session1", query="q1", sector="textiles",
        target_countries=["US"], summary="summary1",
    )

    turns = memory.get_turns("session1")
    assert len(turns) == 1
    assert turns[0].query == "q1"


def test_context_string_empty_for_new_session():
    memory = ConversationMemory()
    assert memory.get_context_string("nonexistent") == ""


def test_context_string_includes_prior_turns():
    memory = ConversationMemory()
    memory.add_turn(
        "session1", query="q1", sector="textiles",
        target_countries=["US"], summary="summary1",
    )
    context = memory.get_context_string("session1")
    assert "q1" in context
    assert "textiles" in context
    assert "US" in context


def test_sessions_are_isolated():
    memory = ConversationMemory()
    memory.add_turn("session1", query="q1", sector="textiles", target_countries=["US"], summary="s1")
    memory.add_turn("session2", query="q2", sector="leather", target_countries=["DE"], summary="s2")

    assert len(memory.get_turns("session1")) == 1
    assert len(memory.get_turns("session2")) == 1
    assert memory.get_turns("session1")[0].query == "q1"
    assert memory.get_turns("session2")[0].query == "q2"


def test_max_turns_per_session_enforced():
    memory = ConversationMemory()
    for i in range(10):
        memory.add_turn(
            "session1", query=f"q{i}", sector="textiles",
            target_countries=["US"], summary=f"s{i}",
        )

    turns = memory.get_turns("session1")
    assert len(turns) == 5  # _MAX_TURNS_PER_SESSION
    # Should keep the most recent, not the oldest.
    assert turns[-1].query == "q9"
    assert turns[0].query == "q5"


def test_clear_session_removes_history():
    memory = ConversationMemory()
    memory.add_turn("session1", query="q1", sector="textiles", target_countries=["US"], summary="s1")
    memory.clear_session("session1")
    assert memory.get_turns("session1") == []


def test_clear_nonexistent_session_does_not_raise():
    memory = ConversationMemory()
    memory.clear_session("never_existed")  # should not raise
