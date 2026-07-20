"""
Database repository — all DB operations in one place.

Routes call these functions; they never write SQL directly.
This keeps the routes thin and makes the DB layer independently testable.

All functions are async and use the async_session context manager.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ConversationTurn,
    OpportunityScore,
    Query,
    Session,
    async_session,
)


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

async def get_or_create_session(session_id: str, provider: str = "openrouter") -> Session:
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        sess = result.scalar_one_or_none()
        if sess is None:
            sess = Session(id=session_id, provider=provider)
            db.add(sess)
            await db.commit()
            await db.refresh(sess)
        return sess


async def update_session_meta(
    session_id: str,
    sector: str | None,
    countries: list[str],
    provider: str,
) -> None:
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        sess = result.scalar_one_or_none()
        if sess:
            sess.last_sector = sector
            sess.last_countries = countries
            sess.provider = provider
            sess.turn_count = (sess.turn_count or 0) + 1
            sess.updated_at = datetime.now(timezone.utc)
            await db.commit()


async def delete_session(session_id: str) -> None:
    async with async_session() as db:
        await db.execute(delete(Session).where(Session.id == session_id))
        await db.commit()


# ------------------------------------------------------------------
# Conversation turns
# ------------------------------------------------------------------

async def save_turn(
    session_id: str,
    turn_index: int,
    query: str,
    sector: str | None,
    target_countries: list[str],
    summary: str,
) -> None:
    async with async_session() as db:
        # Upsert: update if this turn_index already exists, else insert
        result = await db.execute(
            select(ConversationTurn).where(
                ConversationTurn.session_id == session_id,
                ConversationTurn.turn_index == turn_index,
            )
        )
        turn = result.scalar_one_or_none()
        if turn:
            turn.query = query
            turn.sector = sector
            turn.target_countries = target_countries
            turn.summary = summary
        else:
            turn = ConversationTurn(
                session_id=session_id,
                turn_index=turn_index,
                query=query,
                sector=sector,
                target_countries=target_countries,
                summary=summary,
            )
            db.add(turn)
        await db.commit()


async def get_turns(session_id: str) -> list[ConversationTurn]:
    async with async_session() as db:
        result = await db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.turn_index)
        )
        return list(result.scalars().all())


# ------------------------------------------------------------------
# Queries
# ------------------------------------------------------------------

async def save_query(
    session_id: str,
    query_text: str,
    sector: str | None,
    target_countries: list[str],
    provider: str,
    agents_called: list[str],
    summary: str,
    errors: list[str],
    duration_ms: int,
    scores: list[dict],
) -> int:
    """Save a completed query and its scores. Returns the query id."""
    async with async_session() as db:
        q = Query(
            session_id=session_id,
            query_text=query_text,
            sector=sector,
            target_countries=target_countries,
            provider=provider,
            agents_called=agents_called,
            summary=summary,
            errors=errors,
            duration_ms=duration_ms,
        )
        db.add(q)
        await db.flush()  # get q.id without committing

        for s in scores:
            db.add(OpportunityScore(
                query_id=q.id,
                hs_code=s.get("hs_code", ""),
                destination_country=s.get("destination_country", ""),
                score=float(s.get("score", 0)),
                score_breakdown=s.get("score_breakdown", {}),
                note=s.get("note", ""),
            ))

        await db.commit()
        return q.id


async def get_recent_queries(session_id: str, limit: int = 10) -> list[Query]:
    async with async_session() as db:
        result = await db.execute(
            select(Query)
            .where(Query.session_id == session_id)
            .order_by(Query.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
