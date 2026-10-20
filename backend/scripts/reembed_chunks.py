"""Utility script to re-calculate vector embeddings for all Knowledge Chunks and FAQs using the active AI provider (Gemini or Ollama).

Usage:
    python backend/scripts/reembed_chunks.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.config import settings
from app.db import session as db_session
from app.models.knowledge import KnowledgeChunk, FAQItem
from app.services.embedding_service import embedding_service


async def main() -> None:
    print("=" * 65)
    print(" SmartDesk AI - Knowledge Chunks Re-Embedding Utility")
    print(f" Active Provider  : {settings.AI_PROVIDER.upper()}")
    if settings.AI_PROVIDER.lower() == "ollama":
        print(f" Ollama Model     : {settings.OLLAMA_EMBEDDING_MODEL}")
        print(f" Ollama URL       : {settings.OLLAMA_BASE_URL}")
    else:
        print(f" Gemini Model     : {settings.EMBEDDING_MODEL_NAME}")
    print("=" * 65)

    # Initialize DB connection and schema if needed
    await db_session.init_db()

    async with db_session.async_session_factory() as session:
        # 1. Re-embed Knowledge Chunks
        chunks_res = await session.execute(select(KnowledgeChunk))
        chunks = chunks_res.scalars().all()
        print(f"\n[1/2] Processing {len(chunks)} Knowledge Chunks...")

        for idx, chunk in enumerate(chunks, 1):
            emb = await embedding_service.get_text_embedding(chunk.content)
            chunk.embedding = emb
            print(f"  -> Chunk {idx}/{len(chunks)}: '{chunk.title[:40]}' (Dim: {len(emb)})")

        # 2. Re-embed FAQ Items
        faqs_res = await session.execute(select(FAQItem))
        faqs = faqs_res.scalars().all()
        print(f"\n[2/2] Processing {len(faqs)} FAQ Items...")

        for idx, faq in enumerate(faqs, 1):
            emb = await embedding_service.get_text_embedding(faq.content)
            faq.embedding = emb
            print(f"  -> FAQ {idx}/{len(faqs)}: '{faq.title[:40]}' (Dim: {len(emb)})")

        await session.commit()
        print("\n" + "=" * 65)
        print(f" Successfully re-embedded {len(chunks)} chunks and {len(faqs)} FAQs.")
        print(" All vector representations are now aligned with the active provider.")
        print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
