"""RAG (Retrieval-Augmented Generation) pipeline with Circuit Breaker and Citations."""

import time
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.knowledge import FAQItem
from app.schemas.chat import ChatResponse, CitationBadge
from app.services.llm_service import llm_service
from app.services.fallback_service import fallback_service
from app.core.exceptions import LLMTimeoutException, LLMServiceException

logger = logging.getLogger("smartdesk.rag")


class RAGService:
    """Orchestrates document retrieval, grounded prompt synthesis, and fallback routing."""

    async def retrieve_context_documents(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant knowledge articles from database or seed FAQ cache.
        """
        # First attempt to retrieve from DB if session is available
        if session:
            try:
                result = await session.execute(select(FAQItem).limit(top_k * 4))
                db_items = result.scalars().all()
                if db_items:
                    # Score against BM25 index of loaded items
                    temp_docs = [
                        {
                            "doc_id": item.doc_id,
                            "title": item.title,
                            "content": item.content,
                            "category": item.category,
                            "source_url": item.source_url
                        }
                        for item in db_items
                    ]
                    # Score using BM25 engine
                    scored = fallback_service.bm25.score(query)
                    if scored:
                        return [doc for doc, _ in scored[:top_k]]
            except Exception as e:
                logger.warning(f"Database context retrieval failed, using seed cache: {e}")

        # Fallback to in-memory seed FAQ items via BM25
        ranked = fallback_service.bm25.score(query)
        if ranked:
            return [doc for doc, _ in ranked[:top_k]]

        # Return first top_k seed items if query had no strong token match
        return fallback_service.faq_items[:top_k]

    async def answer_query(
        self,
        query: str,
        session: Optional[AsyncSession] = None
    ) -> ChatResponse:
        """
        Executes end-to-end RAG query resolution with automatic Circuit Breaker fallback.
        """
        overall_start = time.perf_counter()

        try:
            # 1. Retrieve relevant knowledge context
            docs = await self.retrieve_context_documents(query, session=session, top_k=3)
            
            if not docs:
                logger.info("No knowledge context found. Triggering FallbackService.")
                fb_result = fallback_service.match_faq(query)
                latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                return ChatResponse(
                    response=fb_result["response"],
                    citations=[CitationBadge(**c) for c in fb_result["citations"]],
                    latency_ms=latency_ms,
                    confidence=fb_result["confidence"],
                    is_fallback=True,
                    escalation_recommended=fb_result.get("escalation_recommended", True)
                )

            # 2. Synthesize Grounded Context Prompt
            context_blocks: List[str] = []
            citations: List[CitationBadge] = []

            for doc in docs:
                context_blocks.append(
                    f"--- Source Document: [{doc['doc_id']}] {doc['title']} ---\n"
                    f"URL: {doc.get('source_url', '')}\n"
                    f"Content: {doc['content']}"
                )
                citations.append(
                    CitationBadge(
                        doc_id=doc["doc_id"],
                        title=doc["title"],
                        source_url=doc.get("source_url", "/docs")
                    )
                )

            grounded_context = "\n\n".join(context_blocks)
            user_prompt = (
                f"Customer Question: {query}\n\n"
                f"Knowledge Base Verified Context:\n{grounded_context}\n\n"
                f"Instructions: Answer the customer's question thoroughly and empathetically based ONLY on the context above. "
                f"If the answer is not in the context, explicitly say so and advise escalating to human support. "
                f"Include citations like [{docs[0]['doc_id']}] when stating specific instructions."
            )

            # 3. Call Google Gemini LLM with hard timeout (4.0s)
            response_text, llm_latency = await llm_service.generate_response(
                prompt=user_prompt,
                temperature=0.2
            )

            total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)

            return ChatResponse(
                response=response_text.strip(),
                citations=citations,
                latency_ms=total_latency_ms,
                confidence=0.92,
                is_fallback=False,
                escalation_recommended=False
            )

        except (LLMTimeoutException, LLMServiceException, Exception) as exc:
            # Circuit Breaker: Catch LLM timeout, rate limit (429), or connectivity error
            total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            logger.warning(
                f"Circuit breaker tripped due to [{type(exc).__name__}: {str(exc)}]. "
                f"Routing immediately to FallbackService..."
            )

            fallback_data = fallback_service.match_faq(query)

            return ChatResponse(
                response=fallback_data["response"],
                citations=[CitationBadge(**c) for c in fallback_data["citations"]],
                latency_ms=total_latency_ms,
                confidence=fallback_data["confidence"],
                is_fallback=True,
                escalation_recommended=fallback_data.get("escalation_recommended", True)
            )


rag_service = RAGService()
