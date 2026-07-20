"""
Query routes — the main API surface ExportAI's frontend calls.

POST /api/v1/query          — free-text query
POST /api/v1/query/structured — structured sector+markets query

Both endpoints:
  1. Resolve conversation context from Redis (or in-process fallback)
  2. Run the orchestrator graph (agents execute in parallel -- see Sprint 6b)
  3. Serialize the result to QueryResponse
  4. Persist the new turn to the session store
  5. Return the response

Keeping query and session store operations in the route layer (not
buried in the orchestrator) makes it easy to add auth, rate limiting,
and request logging at the HTTP boundary without touching agent logic.
"""

import asyncio
import dataclasses
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models.schemas import QueryRequest, QueryResponse, StructuredQueryRequest
from api.services.session_store import SessionStore

router = APIRouter()


def _serialize_agent_output(obj: Any) -> Any:
    """
    Recursively convert dataclasses (agent output types) to plain
    dicts so they can be JSON-serialized by FastAPI. The Streamlit
    dashboard reads agent outputs the same way whether they come from
    a direct service call or an API call.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _serialize_agent_output(v)
            for k, v in dataclasses.asdict(obj).items()
        }
    if isinstance(obj, list):
        return [_serialize_agent_output(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize_agent_output(v) for k, v in obj.items()}
    return obj


_AGENT_OUTPUT_KEYS = [
    "demand_signal_output",
    "scheme_compliance_output",
    "pricing_output",
    "capability_gap_output",
    "logistics_output",
    "risk_output",
    "competitor_output",
    "buyer_discovery_output",
    "fta_output",
    "document_intelligence_output",
    "certification_output",
    "rag_output",
]


def _build_response(session_id: str, result: dict) -> QueryResponse:
    agent_outputs = {
        key: _serialize_agent_output(result.get(key))
        for key in _AGENT_OUTPUT_KEYS
        if result.get(key) is not None
    }

    return QueryResponse(
        session_id=session_id,
        summary=result.get("summary", "No summary generated."),
        opportunity_scores=result.get("opportunity_scores", []),
        sector=result.get("sector"),
        target_countries=result.get("target_countries", []),
        errors=result.get("errors", []),
        agent_outputs=agent_outputs,
    )


@router.post("/query", response_model=QueryResponse)
async def analyze_query(req: QueryRequest) -> QueryResponse:
    """
    Main chat endpoint. Takes a free-text export question, returns a
    full analysis with opportunity scores and agent outputs.
    """
    store = SessionStore()
    context = await store.get_context(req.session_id)

    # Run the orchestrator in a thread pool so FastAPI's event loop
    # isn't blocked by the synchronous LangGraph graph.invoke() call.
    # Sprint 6b replaces this with a fully async graph.
    from orchestrator.graph import analyze_query as run_query
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: run_query(
            req.query,
            provider=req.provider,
            conversation_context=context,
            sme_certifications=req.certifications,
        ),
    )

    await store.save_turn(
        session_id=req.session_id,
        query=req.query,
        sector=result.get("sector"),
        target_countries=result.get("target_countries", []),
        summary=result.get("summary", ""),
    )

    # Persist to PostgreSQL (non-blocking background task)
    import asyncio
    from db.repository import save_query, get_or_create_session
    asyncio.create_task(get_or_create_session(req.session_id, req.provider))
    asyncio.create_task(save_query(
        session_id=req.session_id,
        query_text=req.query,
        sector=result.get("sector"),
        target_countries=result.get("target_countries", []),
        provider=req.provider,
        agents_called=result.get("agents_to_call", []),
        summary=result.get("summary", ""),
        errors=result.get("errors", []),
        duration_ms=0,  # Sprint 6f adds timing middleware
        scores=result.get("opportunity_scores", []),
    ))

    return _build_response(req.session_id, result)


@router.post("/query/structured", response_model=QueryResponse)
async def analyze_structured(req: StructuredQueryRequest) -> QueryResponse:
    """
    Structured input endpoint for sidebar form submissions.
    """
    store = SessionStore()
    context = await store.get_context(req.session_id)

    from orchestrator.graph import analyze_structured as run_structured
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: run_structured(
            sector=req.sector,
            hs_codes=req.hs_codes,
            target_countries=req.target_countries,
            provider=req.provider,
            sme_revenue_cr=req.sme_revenue_cr,
            has_udyam_registration=req.has_udyam_registration,
            sme_certifications=req.certifications,
            conversation_context=context,
        ),
    )

    await store.save_turn(
        session_id=req.session_id,
        query=f"[structured] sector={req.sector}",
        sector=result.get("sector"),
        target_countries=result.get("target_countries", []),
        summary=result.get("summary", ""),
    )

    return _build_response(req.session_id, result)
