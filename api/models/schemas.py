"""
API request and response models.

Pydantic models define the contract between the frontend and the API.
Keeping them here (separate from orchestrator dataclasses) means the
API's public shape can evolve independently of internal agent outputs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Requests
# ------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Free-text query from the chat input."""
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(default="openrouter")
    certifications: list[str] = Field(default_factory=list)


class StructuredQueryRequest(BaseModel):
    """Structured input (sector + markets) from the sidebar form."""
    session_id: str = Field(..., min_length=1, max_length=100)
    sector: str
    hs_codes: list[str]
    target_countries: list[str]
    sme_revenue_cr: float | None = None
    has_udyam_registration: bool = True
    provider: str = Field(default="openrouter")
    certifications: list[str] = Field(default_factory=list)


# ------------------------------------------------------------------
# Responses
# ------------------------------------------------------------------

class OpportunityScore(BaseModel):
    hs_code: str
    destination_country: str
    score: float
    score_breakdown: dict[str, Any]
    note: str


class QueryResponse(BaseModel):
    session_id: str
    summary: str
    opportunity_scores: list[OpportunityScore]
    sector: str | None
    target_countries: list[str]
    errors: list[str]
    # Full agent outputs serialized to dicts for the dashboard.
    # The Streamlit dashboard reads these the same way it read the
    # direct service output -- no dashboard changes needed.
    agent_outputs: dict[str, Any]


class SessionResponse(BaseModel):
    session_id: str
    turn_count: int
    last_sector: str | None
    last_countries: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    agents_registered: int
    redis_available: bool
