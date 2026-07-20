"""
Shared pytest configuration.

Sets DATABASE_URL to SQLite in-memory BEFORE any test module imports
db.models, so the engine is created pointing at the test DB.
Also ensures all tables are created before any test runs and torn
down after the session so tests are fully isolated.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest


@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all DB tables once per test session."""
    from db.models import create_all_tables
    await create_all_tables()
    yield
