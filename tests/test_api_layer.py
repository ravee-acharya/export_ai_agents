"""
Tests for the FastAPI API layer.

Uses FastAPI's TestClient (synchronous) for route tests, and
directly tests the session store logic with a mocked Redis.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ----------------------------------------------------------------
# App fixture
# ----------------------------------------------------------------

@pytest.fixture
def client():
    # Patch the registry import in lifespan so it doesn't need the full
    # orchestrator wired up during import
    with patch("api.main.analyze_query", create=True), \
         patch("api.routes.health.is_redis_available", new=AsyncMock(return_value=False)):
        from api.main import app
        return TestClient(app)


# ----------------------------------------------------------------
# Health routes
# ----------------------------------------------------------------

def test_liveness(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_returns_agent_count(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["agents_registered"] == 13
    assert data["redis_available"] is False  # mocked as unavailable


# ----------------------------------------------------------------
# Schema tests
# ----------------------------------------------------------------

def test_query_request_validates_empty_query():
    from pydantic import ValidationError
    from api.models.schemas import QueryRequest
    with pytest.raises(ValidationError):
        QueryRequest(query="", session_id="s1")


def test_query_request_validates_too_long_query():
    from pydantic import ValidationError
    from api.models.schemas import QueryRequest
    with pytest.raises(ValidationError):
        QueryRequest(query="x" * 2001, session_id="s1")


def test_query_request_valid():
    from api.models.schemas import QueryRequest
    req = QueryRequest(query="export cotton to US", session_id="s1")
    assert req.provider == "openrouter"
    assert req.certifications == []


def test_structured_query_request_valid():
    from api.models.schemas import StructuredQueryRequest
    req = StructuredQueryRequest(
        session_id="s1",
        sector="textiles",
        hs_codes=["6302"],
        target_countries=["US", "AE"],
    )
    assert req.has_udyam_registration is True


# ----------------------------------------------------------------
# Serialization helper
# ----------------------------------------------------------------

def test_serialize_agent_output_handles_dataclass():
    from dataclasses import dataclass
    from api.routes.query import _serialize_agent_output

    @dataclass
    class FakeOutput:
        sector: str
        score: float

    result = _serialize_agent_output(FakeOutput(sector="textiles", score=72.0))
    assert result == {"sector": "textiles", "score": 72.0}


def test_serialize_agent_output_handles_nested():
    from dataclasses import dataclass
    from api.routes.query import _serialize_agent_output

    @dataclass
    class Inner:
        value: int

    @dataclass
    class Outer:
        items: list

    result = _serialize_agent_output(Outer(items=[Inner(1), Inner(2)]))
    assert result == {"items": [{"value": 1}, {"value": 2}]}


def test_serialize_agent_output_handles_none():
    from api.routes.query import _serialize_agent_output
    assert _serialize_agent_output(None) is None


# ----------------------------------------------------------------
# Session store (in-process fallback, no Redis needed)
# ----------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_store_get_empty_context():
    from api.services.session_store import SessionStore
    store = SessionStore()
    with patch("api.services.session_store._get_redis", new=AsyncMock(return_value=None)):
        ctx = await store.get_context("new_session_xyz")
    assert ctx == ""


@pytest.mark.asyncio
async def test_session_store_save_and_retrieve():
    from api.services.session_store import SessionStore, _fallback_memory
    _fallback_memory.clear_session("test_session_api")
    store = SessionStore()
    with patch("api.services.session_store._get_redis", new=AsyncMock(return_value=None)):
        await store.save_turn(
            "test_session_api",
            query="cotton towels to US",
            sector="textiles",
            target_countries=["US"],
            summary="test summary",
        )
        ctx = await store.get_context("test_session_api")
    assert "cotton towels to US" in ctx
    assert "textiles" in ctx


@pytest.mark.asyncio
async def test_session_store_clear():
    from api.services.session_store import SessionStore, _fallback_memory
    _fallback_memory.clear_session("clear_test_session")
    store = SessionStore()
    with patch("api.services.session_store._get_redis", new=AsyncMock(return_value=None)):
        await store.save_turn(
            "clear_test_session",
            query="test",
            sector="textiles",
            target_countries=["US"],
            summary="s",
        )
        await store.clear_session("clear_test_session")
        ctx = await store.get_context("clear_test_session")
    assert ctx == ""


@pytest.mark.asyncio
async def test_session_store_get_session_info_none_for_missing():
    from api.services.session_store import SessionStore
    store = SessionStore()
    with patch("api.services.session_store._get_redis", new=AsyncMock(return_value=None)):
        info = await store.get_session_info("nonexistent_session_abc123")
    assert info is None


# ----------------------------------------------------------------
# ExportService fallback mode (no API_BASE_URL)
# ----------------------------------------------------------------

def test_export_service_uses_local_mode_when_no_api_url(monkeypatch):
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from services.export_service import ExportService, _API_BASE
    # Reimport to pick up the env change
    import importlib
    import services.export_service as svc
    importlib.reload(svc)
    assert svc._API_BASE == ""


def test_export_service_generates_unique_session_ids():
    from services.export_service import ExportService
    s1 = ExportService()
    s2 = ExportService()
    assert s1._session_id != s2._session_id
