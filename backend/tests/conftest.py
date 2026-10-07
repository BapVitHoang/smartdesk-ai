"""Pytest fixtures for SmartDesk AI test suite.
Provides isolated temporary database and clean test environment.
"""

import os
import tempfile
from pathlib import Path
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 1. Configure isolated test database environment BEFORE importing application
_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_temp_db_path = Path(_temp_db.name).resolve().as_posix()
_temp_db.close()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"
os.environ["FALLBACK_SQLITE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"

from app.main import app
from app.db.session import init_db, create_engine_and_factory
import app.db.session as session_module


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Initializes schema and seeds FAQ data in an isolated temporary test database."""
    test_engine, test_factory = create_engine_and_factory(f"sqlite+aiosqlite:///{_temp_db_path}")
    session_module.engine = test_engine
    session_module.async_session_factory = test_factory

    await init_db()

    yield

    try:
        await test_engine.dispose()
    except Exception:
        pass
    try:
        if os.path.exists(_temp_db_path):
            os.remove(_temp_db_path)
    except Exception:
        pass


@pytest_asyncio.fixture
async def client():
    """Asynchronous HTTP test client fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
