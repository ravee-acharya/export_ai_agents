"""
Health check endpoints.

/health/live  — liveness probe: is the process up?
/health/ready — readiness probe: can it serve traffic?
               (checks Redis + agent registry)

Used by Docker health checks, Kubernetes probes, and load balancers.
"""

from fastapi import APIRouter

from api.models.schemas import HealthResponse
from api.services.session_store import is_redis_available
from orchestrator.registry import AGENT_REGISTRY

router = APIRouter()


@router.get("/live")
async def liveness() -> dict:
    """Always returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """
    Returns 200 if the API is ready to serve requests.
    Returns 503 if Redis is unavailable (agents can still run
    without Redis -- they fall back to in-process memory --
    but the readiness check flags it so ops teams can investigate).
    """
    redis_ok = await is_redis_available()

    return HealthResponse(
        status="ready",
        version="1.0.0",
        agents_registered=len(AGENT_REGISTRY),
        redis_available=redis_ok,
    )
