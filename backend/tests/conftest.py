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
_opt_in_test_url = os.getenv("TEST_DATABASE_URL", "").strip()
_temp_db_path = None

if _opt_in_test_url:
    _active_test_db_url = _opt_in_test_url
    os.environ["DATABASE_URL"] = _opt_in_test_url
    os.environ["FALLBACK_SQLITE_URL"] = _opt_in_test_url
else:
    _temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _temp_db_path = Path(_temp_db.name).resolve().as_posix()
    _temp_db.close()
    _active_test_db_url = f"sqlite+aiosqlite:///{_temp_db_path}"
    os.environ["DATABASE_URL"] = _active_test_db_url
    os.environ["FALLBACK_SQLITE_URL"] = _active_test_db_url

from app.main import app
from app.db.session import init_db, create_engine_and_factory
import app.db.session as session_module
from app.models.user import User
from starlette.requests import Request
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
    """Initializes schema and seeds FAQ data in an isolated test database (PostgreSQL if TEST_DATABASE_URL, else SQLite)."""
    custom_kwargs = {}
    if _opt_in_test_url and "postgresql" in _opt_in_test_url:
        from sqlalchemy.pool import NullPool
        custom_kwargs["poolclass"] = NullPool
    test_engine, test_factory = create_engine_and_factory(_active_test_db_url, **custom_kwargs)
    session_module.engine = test_engine
    session_module.async_session_factory = test_factory

    if _opt_in_test_url and "postgresql" in _opt_in_test_url:
        from app.db.base import Base
        async with test_engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
        assert "postgresql" in session_module.engine.url.drivername, "Expected PostgreSQL engine, got fallback!"

    await init_db()

    if _opt_in_test_url and "postgresql" in _opt_in_test_url:
        assert "postgresql" in session_module.engine.url.drivername, (
            f"init_db() silently fell back to SQLite! Engine url is {session_module.engine.url}"
        )

    yield

    try:
        if _opt_in_test_url and "postgresql" in _opt_in_test_url:
            from app.db.base import Base
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()
    except Exception:
        pass
    try:
        if _temp_db_path and os.path.exists(_temp_db_path):
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


def _resolve_test_user_from_request(request: Request) -> User:
    auth_header = request.headers.get("authorization", "")
    if "admin" in auth_header:
        return _test_admin_user
    return _test_regular_user


@pytest_asyncio.fixture
async def admin_client():
    """Authenticated Admin test client via dependency override."""
    app.dependency_overrides[get_current_user] = _resolve_test_user_from_request
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer demo_jwt_token_for_admin@smartdesk.ai"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def user_client():
    """Authenticated Customer test client (an.nguyen@company.vn) via dependency override."""
    app.dependency_overrides[get_current_user] = _resolve_test_user_from_request
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
