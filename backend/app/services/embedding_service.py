"""Embedding Service with Cost-Guard Circuit Breaker and Dual-Mode Vector Search."""

import asyncio
import hashlib
import logging
import math
import random
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk
from app.models.document import Document

logger = logging.getLogger("smartdesk.embedding")


class EmbeddingService:
    """Manages vector embeddings, rate limiting, and dual-mode vector search."""

    def __init__(self) -> None:
        self.rate_limited_until: float = 0.0
        self.api_key: str = settings.GEMINI_API_KEY
        self.model_name: str = settings.EMBEDDING_MODEL_NAME
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initializes Gemini API client if API key is provided."""
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            logger.info("No valid GEMINI_API_KEY for embedding. Using deterministic pseudo-embeddings.")
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._sdk_type = "genai"
        except ImportError:
            try:
                import google.generativeai as gai
                gai.configure(api_key=self.api_key)
                self._client = gai
                self._sdk_type = "generativeai"
            except ImportError:
                self._client = None
                self._sdk_type = None

    def is_rate_limited(self) -> bool:
        """Check whether the service is currently in Free Tier rate limit cooldown."""
        return time.time() < self.rate_limited_until

    def generate_pseudo_embedding(self, text: str, dim: int = 768) -> List[float]:
        """
        Generate a deterministic 768-dimensional normalized unit vector based on text hash.
        Used as zero-cost, high-reliability fallback during rate-limit cooldown or offline mode.
        """
        seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
        seed_int = int.from_bytes(seed_hash[:8], byteorder="big")
        rng = random.Random(seed_int)

        vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two float vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    async def get_text_embedding(self, text: str) -> List[float]:
        """
        Calculates vector embedding with Cost-Guard circuit breaker.
        Falls back automatically to pseudo-embeddings on 429 / cooldown.
        """
        if self.is_rate_limited():
            logger.debug("[Cost-Guard] Embedding rate-limit cooldown active. Using pseudo-embedding.")
            return self.generate_pseudo_embedding(text)

        if not self._client or not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            return self.generate_pseudo_embedding(text)

        try:
            return await asyncio.wait_for(
                self._call_gemini_embedding(text),
                timeout=settings.LLM_TIMEOUT_SECONDS
            )
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                self.rate_limited_until = time.time() + 60.0
                logger.warning(
                    "[Cost-Guard] Free Tier rate limit 429 detected during embedding. "
                    "Locking external API calls for 60 seconds."
                )
            else:
                logger.warning(f"Embedding API call error ({exc}). Falling back to pseudo-embedding.")
            return self.generate_pseudo_embedding(text)

    async def _call_gemini_embedding(self, text: str) -> List[float]:
        """Synchronous wrapper for Gemini Embedding SDK calls."""
        if self._sdk_type == "genai":
            def _sync_call() -> List[float]:
                result = self._client.models.embed_content(
                    model=self.model_name,
                    contents=text
                )
                if hasattr(result, "embedding") and result.embedding:
                    return result.embedding.values or []
                if hasattr(result, "embeddings") and result.embeddings:
                    return result.embeddings[0].values or []
                return []
            emb = await asyncio.to_thread(_sync_call)
            return emb if emb else self.generate_pseudo_embedding(text)

        elif self._sdk_type == "generativeai":
            def _sync_call() -> List[float]:
                result = self._client.embed_content(
                    model=f"models/{self.model_name}",
                    content=text,
                    task_type="retrieval_document"
                )
                return result.get("embedding", [])
            emb = await asyncio.to_thread(_sync_call)
            return emb if emb else self.generate_pseudo_embedding(text)

        return self.generate_pseudo_embedding(text)

    async def get_text_embeddings_batch(
        self, texts: List[str], batch_size: int = 5
    ) -> List[List[float]]:
        """
        Computes embeddings in small batches (max 5 items) with 0.5s throttling to protect Free Tier limits.
        """
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_tasks = [self.get_text_embedding(t) for t in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            all_embeddings.extend(batch_results)

            # Throttle between batches if not last batch and not rate limited
            if i + batch_size < len(texts) and not self.is_rate_limited():
                await asyncio.sleep(0.5)

        return all_embeddings

    async def search_similar_chunks(
        self,
        workspace_id: int,
        query: str,
        top_k: int = 3,
        session: Optional[AsyncSession] = None,
        only_published: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Performs dual-mode cosine similarity search over published knowledge chunks.
        """
        if not session:
            return []

        query_vector = await self.get_text_embedding(query)

        # Query chunks for this workspace
        stmt = (
            select(KnowledgeChunk, Document.status.label("doc_status"))
            .outerjoin(Document, KnowledgeChunk.document_id == Document.id)
            .where(KnowledgeChunk.workspace_id == workspace_id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        scored_chunks: List[Dict[str, Any]] = []
        for chunk, doc_status in rows:
            # If only_published is True, filter out pending/unverified document chunks
            if only_published and chunk.document_id is not None:
                if doc_status != "published":
                    continue

            # Compute Cosine Similarity
            embedding = chunk.embedding
            if not embedding:
                embedding = self.generate_pseudo_embedding(chunk.content)

            score = self.cosine_similarity(query_vector, embedding)
            scored_chunks.append({
                "id": chunk.id,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "workspace_id": chunk.workspace_id,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "title": chunk.title,
                "content": chunk.content,
                "source_url": chunk.source_url,
                "score": round(score, 4)
            })

        # Sort descending by similarity score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]


embedding_service = EmbeddingService()
