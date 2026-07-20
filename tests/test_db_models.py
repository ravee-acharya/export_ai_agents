"""
Tests for db/models.py and db/repository.py.

Uses SQLite in-memory via aiosqlite — no Postgres needed.
conftest.py sets DATABASE_URL and creates tables once per session.
Each test uses a unique session_id to avoid cross-test interference.
"""

import pytest


@pytest.mark.asyncio
async def test_create_session():
    from db.repository import get_or_create_session
    sess = await get_or_create_session("s_create_001", provider="openrouter")
    assert sess.id == "s_create_001"
    assert sess.provider == "openrouter"


@pytest.mark.asyncio
async def test_get_or_create_session_idempotent():
    from db.repository import get_or_create_session
    s1 = await get_or_create_session("s_idem_001")
    s2 = await get_or_create_session("s_idem_001")
    assert s1.id == s2.id


@pytest.mark.asyncio
async def test_update_session_meta():
    from db.repository import get_or_create_session, update_session_meta
    await get_or_create_session("s_meta_001")
    await update_session_meta("s_meta_001", sector="textiles",
                               countries=["US", "AE"], provider="openrouter")
    sess = await get_or_create_session("s_meta_001")
    assert sess.last_sector == "textiles"
    assert "US" in sess.last_countries


@pytest.mark.asyncio
async def test_save_and_get_turns():
    from db.repository import get_or_create_session, save_turn, get_turns
    await get_or_create_session("s_turns_001")
    await save_turn("s_turns_001", 0, "export cotton to US",
                    "textiles", ["US"], "US looks strong.")
    turns = await get_turns("s_turns_001")
    assert len(turns) == 1
    assert turns[0].query == "export cotton to US"
    assert turns[0].sector == "textiles"


@pytest.mark.asyncio
async def test_save_turn_upserts_existing_index():
    from db.repository import get_or_create_session, save_turn, get_turns
    await get_or_create_session("s_upsert_001")
    await save_turn("s_upsert_001", 0, "first", "textiles", ["US"], "s1")
    await save_turn("s_upsert_001", 0, "updated", "leather", ["DE"], "s2")
    turns = await get_turns("s_upsert_001")
    assert len(turns) == 1
    assert turns[0].query == "updated"


@pytest.mark.asyncio
async def test_save_query_and_scores():
    from db.repository import get_or_create_session, save_query, get_recent_queries
    await get_or_create_session("s_query_001")
    qid = await save_query(
        session_id="s_query_001",
        query_text="I export cotton towels",
        sector="textiles",
        target_countries=["US", "AE"],
        provider="openrouter",
        agents_called=["demand_signal", "pricing"],
        summary="UAE is the best market.",
        errors=[],
        duration_ms=3200,
        scores=[
            {"hs_code": "6302", "destination_country": "US",
             "score": 72.0, "score_breakdown": {}, "note": ""},
            {"hs_code": "6302", "destination_country": "AE",
             "score": 81.0, "score_breakdown": {}, "note": ""},
        ],
    )
    assert isinstance(qid, int)
    queries = await get_recent_queries("s_query_001")
    assert len(queries) == 1
    assert queries[0].summary == "UAE is the best market."


@pytest.mark.asyncio
async def test_delete_session_removes_related_data():
    from db.repository import (delete_session, get_or_create_session,
                                get_recent_queries, save_query, save_turn)
    await get_or_create_session("s_del_001")
    await save_turn("s_del_001", 0, "q", "textiles", ["US"], "s")
    await save_query("s_del_001", "q", "textiles", ["US"], "openrouter",
                     [], "summary", [], 100, [])
    await delete_session("s_del_001")
    queries = await get_recent_queries("s_del_001")
    assert queries == []


@pytest.mark.asyncio
async def test_get_turns_returns_empty_for_new_session():
    from db.repository import get_or_create_session, get_turns
    await get_or_create_session("s_empty_001")
    turns = await get_turns("s_empty_001")
    assert turns == []


@pytest.mark.asyncio
async def test_opportunity_scores_stored_with_query():
    from db.models import OpportunityScore, async_session
    from db.repository import get_or_create_session, save_query
    from sqlalchemy import select

    await get_or_create_session("s_scores_001")
    qid = await save_query(
        "s_scores_001", "q", "textiles", ["US"], "openrouter",
        [], "s", [], 100,
        [{"hs_code": "6302", "destination_country": "US",
          "score": 75.5, "score_breakdown": {"demand": 1.2}, "note": "test"}],
    )
    async with async_session() as db:
        result = await db.execute(
            select(OpportunityScore).where(OpportunityScore.query_id == qid)
        )
        scores = result.scalars().all()
    assert len(scores) == 1
    assert scores[0].score == 75.5
    assert scores[0].destination_country == "US"
