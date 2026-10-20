"""Pytest fixtures for SmartDesk AI test suite.
Provides isolated temporary database, clean test environment, and auth clients.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure backend root is always on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 1. Configure isolated test database environment BEFORE importing application
_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_temp_db_path = Path(_temp_db.name).resolve().as_posix()
_temp_db.close()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"
os.environ["FALLBACK_SQLITE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"

from app.main import app
from app.db.session import init_db, create_engine_and_factory
import app.db.session as session_module
from app.models.user import User
from app.core.deps import get_current_user

# Predefined test user objects for dependency injection
_test_admin_user = User(
    id=1,
    email="admin@smartdesk.ai",
    full_name="Quản trị viên SmartDesk",
    role="admin",
    oauth_provider="demo",
    workspace_id=1,
)

_test_regular_user = User(
    id=2,
    email="an.nguyen@company.vn",
    full_name="Nguyễn Văn An",
    role="user",
    oauth_provider="demo",
    workspace_id=1,
)


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
    """Default asynchronous HTTP test client with Admin privileges via dependency override."""
    app.dependency_overrides[get_current_user] = lambda: _test_admin_user
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer demo_jwt_token_for_admin@smartdesk.ai"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def admin_client():
    """Authenticated Admin test client via dependency override."""
    app.dependency_overrides[get_current_user] = lambda: _test_admin_user
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer demo_jwt_token_for_admin@smartdesk.ai"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def user_client():
    """Authenticated Customer test client (an.nguyen@company.vn) via dependency override."""
    app.dependency_overrides[get_current_user] = lambda: _test_regular_user
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer demo_jwt_token_for_an.nguyen@company.vn"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def unauth_client():
    """Unauthenticated HTTP test client (no dependency override, no auth header)."""
    old_override = app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    if old_override is not None:
        app.dependency_overrides[get_current_user] = old_override
