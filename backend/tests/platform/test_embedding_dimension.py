"""Tests for embedding dimension enforcement (MRG-DEF-10)."""

import math
import os
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_embedding_service():
    """Create a test EmbeddingService instance with a fake client."""
    service = EmbeddingService()
    service.provider = "gemini"
    service.rate_limited_until = 0.0
    service.api_key = "AIzaSyTestFakeKey12345"
    return service


@pytest.mark.asyncio
async def test_gemini_request_carries_dimension_parameter(mock_embedding_service):
    """Verify that Gemini embedding API requests explicitly specify output_dimensionality."""
    # Test genai SDK path
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.embedding.values = [0.1] * settings.EMBEDDING_DIMENSIONS
    mock_client.models.embed_content.return_value = mock_res

    mock_embedding_service._client = mock_client
    mock_embedding_service._sdk_type = "genai"

    await mock_embedding_service.get_text_embedding("Test query")

    assert mock_client.models.embed_content.called
    kwargs = mock_client.models.embed_content.call_args.kwargs
    config = kwargs.get("config")
    assert config is not None
    # Check output_dimensionality on config object or dict
    out_dim = getattr(config, "output_dimensionality", None) or (config.get("output_dimensionality") if isinstance(config, dict) else None)
    assert out_dim == settings.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_3072_length_answer_is_rejected_and_falls_back(mock_embedding_service, caplog):
    """Verify that an unexpected 3072-dimensional vector is rejected and falls back safely."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    # Simulate API returning un-truncated 3072 dimensions
    mock_res.embedding.values = [0.05] * 3072
    mock_client.models.embed_content.return_value = mock_res

    mock_embedding_service._client = mock_client
    mock_embedding_service._sdk_type = "genai"

    with caplog.at_level("ERROR"):
        emb = await mock_embedding_service.get_text_embedding("Query triggering 3072 dims")

    # Vector must be rejected: length must be EMBEDDING_DIMENSIONS (768), not 3072
    assert len(emb) == settings.EMBEDDING_DIMENSIONS
    # Must log an error about dimension mismatch
    assert any("dimension" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_768_length_answer_is_accepted_and_normalized(mock_embedding_service):
    """Verify that a 768-dimensional vector is accepted and normalized."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    # Non-normalized vector of dimension 768
    raw_vec = [2.0] * settings.EMBEDDING_DIMENSIONS
    mock_res.embedding.values = raw_vec
    mock_client.models.embed_content.return_value = mock_res

    mock_embedding_service._client = mock_client
    mock_embedding_service._sdk_type = "genai"

    emb = await mock_embedding_service.get_text_embedding("Query with 768 dims")

    assert len(emb) == settings.EMBEDDING_DIMENSIONS
    # Norm must be 1.0 (within floating point precision)
    norm = math.sqrt(sum(x * x for x in emb))
    assert abs(norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_document_and_query_paths_covered(mock_embedding_service):
    """Verify that both single query embedding and batch document chunk embeddings enforce dimensions."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.embedding.values = [0.1] * settings.EMBEDDING_DIMENSIONS
    mock_client.models.embed_content.return_value = mock_res

    mock_embedding_service._client = mock_client
    mock_embedding_service._sdk_type = "genai"

    # Query path
    query_emb = await mock_embedding_service.get_text_embedding("Single query")
    assert len(query_emb) == settings.EMBEDDING_DIMENSIONS

    # Document chunk batch path
    doc_chunks = ["Chunk 1 content", "Chunk 2 content"]
    doc_embs = await mock_embedding_service.get_text_embeddings_batch(doc_chunks)
    assert len(doc_embs) == 2
    for emb in doc_embs:
        assert len(emb) == settings.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_postgresql_store_and_query_768_vector():
    """Verify storing and querying 768-dim vector on PostgreSQL using pgvector <=> operator."""
    pg_url = os.environ.get("TEST_DATABASE_URL")
    if not pg_url or "postgresql" not in pg_url:
        pytest.skip("TEST_DATABASE_URL for PostgreSQL is not set; skipping live PostgreSQL test")

    from app.db.session import create_engine_and_factory
    from app.db.base import Base

    engine, session_factory = create_engine_and_factory(pg_url)
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    service = EmbeddingService()
    test_vec = service.generate_pseudo_embedding("PostgreSQL 768-dim test vector", dim=settings.EMBEDDING_DIMENSIONS)
    assert len(test_vec) == settings.EMBEDDING_DIMENSIONS

    async with session_factory() as session:
        chunk = KnowledgeChunk(
            chunk_id="test-pg-dim-768",
            parent_doc_id="test-doc-dim",
            workspace_id=999,
            title="768 Dim Test",
            content="Testing 768 dim storage in PostgreSQL",
            source_url="/test/dim-768",
            embedding=test_vec
        )
        session.add(chunk)
        await session.commit()

        # Query using pgvector cosine distance <=>
        stmt = (
            select(KnowledgeChunk, (1 - KnowledgeChunk.embedding.cosine_distance(test_vec)).label("score"))
            .where(KnowledgeChunk.chunk_id == "test-pg-dim-768")
        )
        res = await session.execute(stmt)
        row = res.first()
        assert row is not None
        fetched_chunk, score = row
        assert fetched_chunk.chunk_id == "test-pg-dim-768"
        assert float(score) > 0.99  # Identical vector has cosine similarity ~1.0

        # Cleanup
        await session.delete(fetched_chunk)
        await session.commit()

    await engine.dispose()

