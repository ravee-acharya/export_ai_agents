"""
Session management routes.

GET  /api/v1/sessions/{session_id}        — get session info
DELETE /api/v1/sessions/{session_id}      — clear session history

The frontend can call DELETE to implement a "New conversation" button
without needing to generate a new session_id.
"""

from fastapi import APIRouter, HTTPException

from api.models.schemas import SessionResponse
from api.services.session_store import SessionStore

router = APIRouter()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    store = SessionStore()
    info = await store.get_session_info(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**info)


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str) -> dict:
    store = SessionStore()
    await store.clear_session(session_id)
    return {"session_id": session_id, "cleared": True}
