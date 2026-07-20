"""
Session store — Redis with in-process fallback.

Redis is the production session backend. If Redis is unavailable
(local dev without Docker, Streamlit Cloud free tier) the store
transparently falls back to the existing in-process ConversationMemory.

Production behaviour:
  - Connection pooled (max 20 connections per worker)
  - Lazy connect with retry on every request if last attempt failed
    (fixes the "cached None never retries after Redis recovers" bug)
  - TTL refreshed on every write so active sessions don't expire
  - 2s socket timeout so a slow Redis doesn't stall the API

Redis key schema:
  exportai:session:{session_id}:turns  — JSON list of turn dicts, capped at 5
  exportai:session:{session_id}:meta   — JSON dict {last_sector, last_countries}

TTL: SESSION_TTL_SECONDS env var (default 86400 = 24h), refreshed on every turn.
"""

import json
import os

from orchestrator.memory import ConversationMemory

_SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", 86400))
_KEY_PREFIX = "exportai:session"
_MAX_TURNS = 5

# In-process fallback — one instance per worker process.
_fallback_memory = ConversationMemory()

# Redis client cache. None = not yet tried or last attempt failed.
# We retry on every request after a failure so the store self-heals
# when Redis comes back after a restart/deploy.
_redis_client = None
_redis_last_failed = False


async def _get_redis():
    """
    Lazy Redis connection with self-healing retry.

    Returns a connected client, or None if Redis is unavailable.
    Retries on every call after a failure (not just on startup) so
    the store recovers automatically when Redis comes back.
    """
    global _redis_client, _redis_last_failed

    # Return cached healthy client
    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            # Client went stale (Redis restarted, network blip)
            _redis_client = None
            _redis_last_failed = True

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=20,          # connection pool size per worker
            socket_timeout=2,            # don't stall the API for slow Redis
            socket_connect_timeout=2,
            socket_keepalive=True,
        )
        await client.ping()
        _redis_client = client
        _redis_last_failed = False
        return _redis_client
    except Exception:
        _redis_client = None
        _redis_last_failed = True
        return None


async def is_redis_available() -> bool:
    """Used by the health endpoint."""
    return await _get_redis() is not None


class SessionStore:
    """
    Unified interface for session persistence.
    Callers never know whether they're talking to Redis or the fallback.
    """

    async def get_context(self, session_id: str) -> str:
        """Return the formatted prior-turn context string for this session."""
        redis = await _get_redis()
        if redis:
            return await self._redis_get_context(redis, session_id)
        return _fallback_memory.get_context_string(session_id)

    async def save_turn(
        self,
        session_id: str,
        query: str,
        sector: str | None,
        target_countries: list[str],
        summary: str,
    ) -> None:
        redis = await _get_redis()
        if redis:
            await self._redis_save_turn(
                redis, session_id, query, sector, target_countries, summary
            )
        else:
            _fallback_memory.add_turn(
                session_id,
                query=query,
                sector=sector,
                target_countries=target_countries,
                summary=summary,
            )

    async def get_session_info(self, session_id: str) -> dict | None:
        redis = await _get_redis()
        if redis:
            return await self._redis_get_info(redis, session_id)
        turns = _fallback_memory.get_turns(session_id)
        if not turns:
            return None
        last = turns[-1]
        return {
            "session_id": session_id,
            "turn_count": len(turns),
            "last_sector": last.sector,
            "last_countries": last.target_countries,
        }

    async def clear_session(self, session_id: str) -> None:
        redis = await _get_redis()
        if redis:
            await redis.delete(
                f"{_KEY_PREFIX}:{session_id}:turns",
                f"{_KEY_PREFIX}:{session_id}:meta",
            )
        else:
            _fallback_memory.clear_session(session_id)

    # ------------------------------------------------------------------
    # Redis implementation
    # ------------------------------------------------------------------

    async def _redis_get_context(self, redis, session_id: str) -> str:
        raw = await redis.get(f"{_KEY_PREFIX}:{session_id}:turns")
        if not raw:
            return ""
        turns = json.loads(raw)
        lines = []
        for i, t in enumerate(turns, 1):
            countries = ", ".join(t.get("target_countries") or []) or "unspecified"
            lines.append(
                f'Turn {i}: asked about "{t["query"]}" '
                f'(sector: {t.get("sector") or "unspecified"}, markets: {countries}). '
                f'Summary given: {t.get("summary", "")[:200]}'
            )
        return "\n".join(lines)

    async def _redis_save_turn(
        self,
        redis,
        session_id: str,
        query: str,
        sector: str | None,
        target_countries: list[str],
        summary: str,
    ) -> None:
        turns_key = f"{_KEY_PREFIX}:{session_id}:turns"
        meta_key  = f"{_KEY_PREFIX}:{session_id}:meta"

        # Read → append → trim → write as a pipeline (atomic-ish)
        async with redis.pipeline(transaction=True) as pipe:
            pipe.get(turns_key)
            pipe.get(meta_key)
            results = await pipe.execute()

        raw_turns, _ = results
        turns = json.loads(raw_turns) if raw_turns else []
        turns.append({
            "query": query,
            "sector": sector,
            "target_countries": target_countries,
            "summary": summary,
        })
        if len(turns) > _MAX_TURNS:
            turns = turns[-_MAX_TURNS:]

        meta = {"last_sector": sector, "last_countries": target_countries}

        # Write both keys with TTL refresh in a pipeline
        async with redis.pipeline(transaction=True) as pipe:
            pipe.set(turns_key, json.dumps(turns), ex=_SESSION_TTL)
            pipe.set(meta_key,  json.dumps(meta),  ex=_SESSION_TTL)
            await pipe.execute()

    async def _redis_get_info(self, redis, session_id: str) -> dict | None:
        turns_key = f"{_KEY_PREFIX}:{session_id}:turns"
        meta_key  = f"{_KEY_PREFIX}:{session_id}:meta"

        async with redis.pipeline() as pipe:
            pipe.get(turns_key)
            pipe.get(meta_key)
            raw_turns, raw_meta = await pipe.execute()

        if not raw_turns:
            return None

        turns = json.loads(raw_turns)
        meta  = json.loads(raw_meta) if raw_meta else {}
        return {
            "session_id": session_id,
            "turn_count": len(turns),
            "last_sector": meta.get("last_sector"),
            "last_countries": meta.get("last_countries", []),
        }
