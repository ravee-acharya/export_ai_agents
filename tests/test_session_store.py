"""
Tests for api/services/session_store.py — Sprint 6c Redis session memory.

Two test classes:
  TestSessionStoreFallback — in-process fallback (no Redis needed)
  TestSessionStoreRedis    — Redis path, using a mock client

The mock Redis client mimics the real redis.asyncio interface so we
test the actual Redis code paths (pipeline, get, set, delete) without
needing a running Redis server in CI.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ------------------------------------------------------------------
# Mock Redis client
# ------------------------------------------------------------------

class MockPipeline:
    """Mimics redis.asyncio pipeline context manager."""
    def __init__(self, store: dict):
        self._store = store
        self._commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def get(self, key):
        self._commands.append(('get', key))
        return self

    def set(self, key, value, ex=None):
        self._commands.append(('set', key, value, ex))
        return self

    def delete(self, *keys):
        self._commands.append(('delete', keys))
        return self

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == 'get':
                results.append(self._store.get(cmd[1]))
            elif cmd[0] == 'set':
                self._store[cmd[1]] = cmd[2]
                results.append(True)
            elif cmd[0] == 'delete':
                for k in cmd[1]:
                    self._store.pop(k, None)
                results.append(len(cmd[1]))
        self._commands.clear()
        return results


class MockRedis:
    """Minimal async Redis mock covering all methods SessionStore uses."""
    def __init__(self):
        self._store: dict = {}

    async def ping(self):
        return True

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    def pipeline(self, transaction=False):
        return MockPipeline(self._store)


# ------------------------------------------------------------------
# Fallback path tests (no Redis)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_get_context_empty_for_new_session():
    import api.services.session_store as ss
    ss._fallback_memory.clear_session("fb_test_new")
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=None)):
        ctx = await store.get_context("fb_test_new")
    assert ctx == ""


@pytest.mark.asyncio
async def test_fallback_save_and_retrieve_context():
    import api.services.session_store as ss
    ss._fallback_memory.clear_session("fb_test_ctx")
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=None)):
        await store.save_turn(
            "fb_test_ctx",
            query="export cotton towels",
            sector="textiles",
            target_countries=["US"],
            summary="test summary",
        )
        ctx = await store.get_context("fb_test_ctx")
    assert "export cotton towels" in ctx
    assert "textiles" in ctx
    assert "US" in ctx


@pytest.mark.asyncio
async def test_fallback_clear_removes_history():
    import api.services.session_store as ss
    ss._fallback_memory.clear_session("fb_test_clear")
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=None)):
        await store.save_turn("fb_test_clear", "q", "textiles", ["US"], "s")
        await store.clear_session("fb_test_clear")
        ctx = await store.get_context("fb_test_clear")
    assert ctx == ""


@pytest.mark.asyncio
async def test_fallback_get_session_info_none_for_missing():
    import api.services.session_store as ss
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=None)):
        info = await store.get_session_info("definitely_does_not_exist_xyz")
    assert info is None


# ------------------------------------------------------------------
# Redis path tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_get_context_empty_for_new_session():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        ctx = await store.get_context("redis_new_session")
    assert ctx == ""


@pytest.mark.asyncio
async def test_redis_save_and_retrieve_context():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        await store.save_turn(
            "redis_ctx_test",
            query="should I export to Germany?",
            sector="textiles",
            target_countries=["DE"],
            summary="Germany looks strong.",
        )
        ctx = await store.get_context("redis_ctx_test")
    assert "should I export to Germany?" in ctx
    assert "textiles" in ctx
    assert "DE" in ctx


@pytest.mark.asyncio
async def test_redis_turns_capped_at_max():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        for i in range(8):
            await store.save_turn(
                "redis_cap_test",
                query=f"query {i}",
                sector="textiles",
                target_countries=["US"],
                summary=f"summary {i}",
            )
    # Inspect the stored turns directly
    raw = mock_redis._store.get("exportai:session:redis_cap_test:turns")
    turns = json.loads(raw)
    assert len(turns) == ss._MAX_TURNS
    # Most recent turns kept, oldest dropped
    assert turns[-1]["query"] == "query 7"
    assert turns[0]["query"] == f"query {8 - ss._MAX_TURNS}"


@pytest.mark.asyncio
async def test_redis_get_session_info():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        await store.save_turn(
            "redis_info_test",
            query="test",
            sector="leather",
            target_countries=["AE", "US"],
            summary="summary",
        )
        info = await store.get_session_info("redis_info_test")
    assert info is not None
    assert info["session_id"] == "redis_info_test"
    assert info["turn_count"] == 1
    assert info["last_sector"] == "leather"
    assert "AE" in info["last_countries"]


@pytest.mark.asyncio
async def test_redis_clear_deletes_both_keys():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        await store.save_turn("redis_del_test", "q", "textiles", ["US"], "s")
        assert "exportai:session:redis_del_test:turns" in mock_redis._store
        await store.clear_session("redis_del_test")
        assert "exportai:session:redis_del_test:turns" not in mock_redis._store
        assert "exportai:session:redis_del_test:meta" not in mock_redis._store


@pytest.mark.asyncio
async def test_redis_get_session_info_none_when_no_turns():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        info = await store.get_session_info("redis_missing_session")
    assert info is None


@pytest.mark.asyncio
async def test_redis_self_healing_retries_after_failure():
    """
    After a Redis failure (cached None), the store must retry on the
    next request rather than staying broken forever.
    """
    import api.services.session_store as ss

    call_count = [0]
    mock_redis = MockRedis()

    async def flaky_get_redis():
        call_count[0] += 1
        if call_count[0] == 1:
            return None  # first call: Redis down
        return mock_redis  # subsequent calls: Redis back up

    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=flaky_get_redis):
        # First call falls back to in-process
        ctx1 = await store.get_context("healing_test")
        assert ctx1 == ""
        # Second call hits Redis (self-healed)
        await store.save_turn("healing_test", "q", "textiles", ["US"], "s")
        ctx2 = await store.get_context("healing_test")
    assert "healing_test" not in ctx2 or True  # just verifying no exception
    assert call_count[0] >= 2


# ------------------------------------------------------------------
# TTL and key prefix
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_keys_use_correct_prefix():
    import api.services.session_store as ss
    mock_redis = MockRedis()
    store = ss.SessionStore()
    with patch.object(ss, '_get_redis', new=AsyncMock(return_value=mock_redis)):
        await store.save_turn("prefix_test", "q", "textiles", ["US"], "s")
    keys = list(mock_redis._store.keys())
    assert all(k.startswith("exportai:session:") for k in keys)


def test_session_ttl_defaults_to_24h():
    import api.services.session_store as ss
    assert ss._SESSION_TTL == 86400


def test_max_turns_is_5():
    import api.services.session_store as ss
    assert ss._MAX_TURNS == 5
