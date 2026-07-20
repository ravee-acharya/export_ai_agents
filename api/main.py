"""
ExportAI FastAPI backend.

Entry point for the production API. Streamlit (or any other frontend)
calls this instead of instantiating ExportService directly. This
separation means:
  - The frontend is stateless (no Python service objects in memory)
  - Multiple Streamlit replicas can share one API backend
  - The API can be called by mobile apps, partner integrations, etc.
  - Each layer (API, agents, DB) can be scaled independently

Run locally:
    uvicorn api.main:app --reload --port 8000

Run in Docker:
    see docker-compose.yml
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.logging import LoggingMiddleware
from api.routes import health, query, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Ensure DB tables exist (idempotent — safe to run on every start)
    from db.models import create_all_tables
    await create_all_tables()
    # Warm the agent registry so the first request isn't slow
    from orchestrator.registry import AGENT_REGISTRY  # noqa: F401
    yield
    # Shutdown: dispose the DB connection pool cleanly
    from db.models import engine
    await engine.dispose()


app = FastAPI(
    title="ExportAI API",
    description="AI-powered export intelligence for Indian SME exporters.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow Streamlit Cloud and local dev origins.
# Tighten this list before going fully public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",          # local Streamlit
        "https://*.streamlit.app",        # Streamlit Cloud
        "*",                              # TODO: restrict before public launch
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(query.router,  prefix="/api/v1", tags=["query"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
