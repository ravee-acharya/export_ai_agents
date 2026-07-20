"""
PostgreSQL database models — SQLAlchemy 2.x async ORM.

Tables:
  sessions        — one row per Streamlit/API session
  conversation_turns — the chat history per session (max 5 kept)
  queries         — every query ever run, with input + output
  opportunity_scores — normalised score rows from each query

Why async SQLAlchemy:
  The FastAPI routes are async (Sprint 6a). Using async SQLAlchemy
  means DB calls are non-blocking — the event loop can handle other
  requests while waiting for Postgres. Sync SQLAlchemy inside an
  async route would block the event loop.

Connection:
  DATABASE_URL env var (default: sqlite+aiosqlite for local dev
  without Postgres). In Docker, docker-compose.yml sets it to the
  Postgres container.

Usage:
  from db.models import async_session, Session, Query

  async with async_session() as session:
      q = Query(session_id="abc", query_text="export cotton...")
      session.add(q)
      await session.commit()
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

# Local dev: SQLite (no Postgres needed). Production: Postgres via Docker.
_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./exportai_dev.db",
)

# Convert sync postgres:// URLs (from some hosting platforms) to async
_DATABASE_URL = _DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace(
    "postgres://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    **({
        "pool_size": 10,
        "max_overflow": 20,
    } if "postgresql" in _DATABASE_URL else {}),
)

# SQLite requires PRAGMA foreign_keys=ON per connection for CASCADE to work.
# This is a no-op on PostgreSQL.
from sqlalchemy import event as _sa_event

@_sa_event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass  # Not SQLite, ignore

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    """One row per user session (browser tab / Streamlit session)."""

    __tablename__ = "sessions"

    id = Column(String(100), primary_key=True)  # UUID from ExportService
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    provider = Column(String(50), default="openrouter")
    turn_count = Column(Integer, default=0)
    last_sector = Column(String(200))
    last_countries = Column(JSON)  # list[str]

    turns = relationship("ConversationTurn", back_populates="session",
                         cascade="all, delete-orphan", order_by="ConversationTurn.turn_index")
    queries = relationship("Query", back_populates="session",
                           cascade="all, delete-orphan")


class ConversationTurn(Base):
    """Conversation history — max 5 per session (enforced by SessionStore)."""

    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), ForeignKey("sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    turn_index = Column(Integer, nullable=False)
    query = Column(Text, nullable=False)
    sector = Column(String(200))
    target_countries = Column(JSON)  # list[str]
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    session = relationship("Session", back_populates="turns")

    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_session_turn"),
    )


class Query(Base):
    """
    Every query run — input, output, timing, errors.
    Useful for analytics, debugging, and future fine-tuning datasets.
    """

    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), ForeignKey("sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    sector = Column(String(200))
    target_countries = Column(JSON)
    provider = Column(String(50))
    agents_called = Column(JSON)        # list[str]
    summary = Column(Text)
    errors = Column(JSON)               # list[str]
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    session = relationship("Session", back_populates="queries")
    scores = relationship("OpportunityScore", back_populates="query",
                          cascade="all, delete-orphan")


class OpportunityScore(Base):
    """
    Normalised opportunity scores — one row per (query, hs_code, country).
    Keeping scores in their own table allows time-series analytics:
    "how has the US cotton market score changed over time?"
    """

    __tablename__ = "opportunity_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"),
                      nullable=False, index=True)
    hs_code = Column(String(20), nullable=False)
    destination_country = Column(String(10), nullable=False, index=True)
    score = Column(Float, nullable=False)
    score_breakdown = Column(JSON)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)

    query = relationship("Query", back_populates="scores")


async def create_all_tables() -> None:
    """Create all tables. Called on API startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
