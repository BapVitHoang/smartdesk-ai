"""Async Database session configuration and lifecycle initialization."""

from typing import AsyncGenerator
import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy import select

from app.core.config import BACKEND_DIR, settings
from app.db.base import Base

logger = logging.getLogger("smartdesk.db")


def normalize_database_url(url: str) -> str:
    """Ensure database connection URL uses an asynchronous driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def create_engine_and_factory(url: str):
    """Factory helper to build async engine and session factory."""
    norm_url = normalize_database_url(url)
    kwargs = {"echo": settings.DEBUG}
    if "sqlite" in norm_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    eng = create_async_engine(norm_url, **kwargs)
    factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    return eng, factory


engine, async_session_factory = create_engine_and_factory(settings.DATABASE_URL)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the active async session factory (safe across SQLite fallback re-binds)."""
    return async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables and seed initial FAQ data if empty."""
    global engine, async_session_factory
    from app.models.ticket import Ticket  # noqa: F401
    from app.models.knowledge import FAQItem, KnowledgeChunk  # noqa: F401
    from app.models.workspace import Workspace  # noqa: F401
    from app.models.document import Document  # noqa: F401
    from app.models.verification import VerificationReport, VerificationItem  # noqa: F401
    from app.models.user import User  # noqa: F401

    def _migrate_sqlite_columns(sync_conn):
        try:
            ticket_cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(tickets)").fetchall()]
            if ticket_cols and "workspace_id" not in ticket_cols:
                sync_conn.exec_driver_sql("ALTER TABLE tickets ADD COLUMN workspace_id INTEGER DEFAULT 1")
            
            kc_cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(knowledge_chunks)").fetchall()]
            if kc_cols:
                if "workspace_id" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN workspace_id INTEGER DEFAULT 1")
                if "document_id" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN document_id INTEGER")
                if "chunk_index" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN chunk_index INTEGER DEFAULT 0")
                if "page_number" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN page_number INTEGER DEFAULT 1")

            user_cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
            if user_cols:
                if "google_sub" not in user_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)")
                if "avatar_url" not in user_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512)")
                if "is_active" not in user_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
                if "updated_at" not in user_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE users ADD COLUMN updated_at DATETIME")
        except Exception as mig_err:
            logger.warning(f"SQLite auto-migration notice: {mig_err}")

    # 1. Synchronize schema, falling back to SQLite if PostgreSQL fails
    try:
        async with engine.begin() as conn:
            if "postgresql" in engine.url.drivername:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in engine.url.drivername:
                await conn.run_sync(_migrate_sqlite_columns)
        logger.info(f"Database schema synchronized successfully on {engine.url.drivername}.")
    except Exception as e:
        logger.warning(
            f"Primary database connection failed ({e}). "
            f"Falling back to local async SQLite: {settings.FALLBACK_SQLITE_URL}"
        )
        engine, async_session_factory = create_engine_and_factory(settings.FALLBACK_SQLITE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_migrate_sqlite_columns)
        logger.info("Database schema synchronized on fallback SQLite engine.")

    # 2. Seed initial data via modular db/seed package
    try:
        from app.db.seed import seed_all
        async with async_session_factory() as session:
            await seed_all(session)
    except Exception as e:
        logger.error(f"Error during database initialization/seeding: {e}", exc_info=True)
        # For non-fatal database initialization failure, allow fallback
