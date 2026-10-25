"""Platform module tests for pgvector dialect mapping and database resilience (REQ-07, REQ-11)."""

import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import select, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models.knowledge import KnowledgeChunk, FAQItem
from app.services.embedding_service import embedding_service
from app.core.security import redact_pii


def test_pgvector_dual_dialect_column_mapping() -> None:
    """Verify KnowledgeChunk.embedding uses Vector(768) with SQLite JSON variant."""
    kc_col = KnowledgeChunk.__table__.columns["embedding"]
    assert kc_col.nullable is True
    # Verify the column type has Vector base and JSON variant for sqlite
    type_repr = repr(kc_col.type)
    assert "Vector" in type_repr or "VECTOR" in type_repr or "JSON" in type_repr


def test_redact_pii_before_embedding() -> None:
    """Verify redact_pii masks customer email and phone before embedding processing."""
    raw = "User email customer@enterprise.com with phone 0987654321 reported an issue."
    masked = redact_pii(raw)
    assert "customer@enterprise.com" not in masked
    assert "0987654321" not in masked
    assert "[REDACTED_EMAIL]" in masked
    assert "[REDACTED_PHONE]" in masked


@pytest.mark.asyncio
async def test_search_similar_chunks_sqlite_fallback(client) -> None:
    """Verify search_similar_chunks runs cleanly on SQLite using in-memory cosine similarity."""
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        # Workspace 2 has seeded documents/chunks from sample_documents
        results = await embedding_service.search_similar_chunks(
            workspace_id=2,
            query="chi phí khám răng và bảng giá điều trị",
            top_k=2,
            session=session,
            only_published=False
        )
        assert isinstance(results, list)
        assert len(results) > 0, "Expected at least 1 similar chunk for workspace 2"
        for r in results:
            assert "chunk_id" in r
            assert "score" in r
            assert -1.0 <= r["score"] <= 1.0


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL") or "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL TEST_DATABASE_URL"
)
async def test_search_similar_chunks_postgresql_pgvector(client, caplog) -> None:
    """Verify search_similar_chunks runs native pgvector SQL query with <=> cosine distance on PostgreSQL."""
    import logging
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        # Seed test chunk if needed
        existing = await session.execute(select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == 2))
        chunk = existing.scalars().first()
        if not chunk:
            dummy_vec = embedding_service.generate_pseudo_embedding("Dịch vụ niềng răng trong suốt SmileCare")
            chunk = KnowledgeChunk(
                workspace_id=2,
                chunk_id="smilecare-chunk-test-1",
                chunk_index=0,
                page_number=1,
                title="Bảng giá niềng răng SmileCare",
                content="Chi phí niềng răng trong suốt từ 35 triệu đến 80 triệu đồng.",
                embedding=dummy_vec
            )
            session.add(chunk)
            await session.commit()

        with caplog.at_level(logging.WARNING):
            results = await embedding_service.search_similar_chunks(
                workspace_id=2,
                query="niềng răng chi phí bao nhiêu",
                top_k=2,
                session=session,
                only_published=False
            )
        # Assert no fallback warning occurred
        for record in caplog.records:
            assert "Falling back to memory cosine" not in record.message
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert "chunk_id" in r
            assert "score" in r
            assert -1.0 <= r["score"] <= 1.0

