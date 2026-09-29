"""RAG (Retrieval-Augmented Generation) pipeline with Workspace Persona, Citations, and Cost-Guard Circuit Breaker."""

import time
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.knowledge import FAQItem
from app.models.workspace import Workspace
from app.schemas.chat import ChatResponse, CitationBadge
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.services.fallback_service import fallback_service
from app.core.exceptions import LLMTimeoutException, LLMServiceException

logger = logging.getLogger("smartdesk.rag")


class RAGService:
    """Orchestrates workspace-aware document retrieval, grounded persona prompt synthesis, and fallback routing."""

    async def retrieve_context_documents(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[int] = 1,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant knowledge articles from workspace vector chunks or seed FAQ cache.
        """
        ws_id = workspace_id or 1
        docs: List[Dict[str, Any]] = []

        # 1. Search fine-grained chunks in the specified workspace
        if session:
            try:
                similar_chunks = await embedding_service.search_similar_chunks(
                    workspace_id=ws_id,
                    query=query,
                    top_k=top_k,
                    session=session,
                    only_published=True
                )
                for chk in similar_chunks:
                    # Filter out low-relevance chunks if score < 0.2
                    docs.append({
                        "doc_id": chk["chunk_id"],
                        "title": chk["title"],
                        "content": chk["content"],
                        "category": "Workspace Document",
                        "source_url": chk["source_url"],
                        "page": chk.get("page_number", 1),
                        "snippet": chk["content"][:160] + "..." if len(chk["content"]) > 160 else chk["content"],
                        "score": chk.get("score", 0.8)
                    })
            except Exception as e:
                logger.warning(f"Workspace chunk retrieval failed: {e}")

        # 2. For default workspace or if no chunks found, blend with curated FAQ items
        if len(docs) < top_k and ws_id == 1:
            if session:
                try:
                    result = await session.execute(select(FAQItem).limit(top_k * 4))
                    db_items = result.scalars().all()
                    if db_items:
                        scored = fallback_service.bm25.score(query)
                        if scored:
                            for item_doc, score_val in scored[: top_k - len(docs)]:
                                docs.append({
                                    "doc_id": item_doc["doc_id"],
                                    "title": item_doc["title"],
                                    "content": item_doc["content"],
                                    "category": item_doc.get("category", "General"),
                                    "source_url": item_doc.get("source_url", "/docs"),
                                    "page": 1,
                                    "snippet": item_doc["content"][:160] + "...",
                                    "score": 0.85
                                })
                except Exception as e:
                    logger.warning(f"Database FAQ retrieval failed: {e}")

            if len(docs) < top_k:
                ranked = fallback_service.bm25.score(query)
                if ranked:
                    for doc_item, _ in ranked[: top_k - len(docs)]:
                        docs.append({
                            "doc_id": doc_item["doc_id"],
                            "title": doc_item["title"],
                            "content": doc_item["content"],
                            "category": doc_item.get("category", "General"),
                            "source_url": doc_item.get("source_url", "/docs"),
                            "page": 1,
                            "snippet": doc_item["content"][:160] + "...",
                            "score": 0.80
                        })

        return docs[:top_k]

    async def answer_query(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[int] = None
    ) -> ChatResponse:
        """
        Executes end-to-end RAG query resolution with Workspace Persona and Cost-Guard Circuit Breaker fallback.
        """
        overall_start = time.perf_counter()
        ws_id = workspace_id or 1

        # Resolve Workspace Persona
        persona_name = "SmartDesk Assistant"
        ws_name = "SmartDesk Cloud Support"
        industry = "IT & SaaS"
        tone_of_voice = "Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật."
        business_rules = "Hỗ trợ xử lý sự cố tài khoản, phân quyền, tích hợp API, thanh toán định kỳ. Luôn bảo vệ an toàn thông tin khách hàng."

        if session:
            try:
                ws_res = await session.execute(select(Workspace).where(Workspace.id == ws_id))
                ws_obj = ws_res.scalar_one_or_none()
                if ws_obj:
                    persona_name = ws_obj.persona_name
                    ws_name = ws_obj.name
                    industry = ws_obj.industry
                    tone_of_voice = ws_obj.tone_of_voice
                    business_rules = ws_obj.business_rules
            except Exception as e:
                logger.warning(f"Error loading workspace {ws_id}: {e}")

        # Check if already in Free Tier cooldown
        if llm_service.is_in_cooldown():
            logger.warning("[Cost-Guard] Free Tier cooldown active. Fast-pathing to FallbackService.")
            fb_result = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name)
            latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            return ChatResponse(
                response=fb_result["response"],
                citations=[CitationBadge(**c) for c in fb_result["citations"]],
                latency_ms=latency_ms,
                confidence=fb_result["confidence"],
                is_fallback=True,
                fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN",
                escalation_recommended=fb_result.get("escalation_recommended", True)
            )

        try:
            # 1. Retrieve relevant knowledge context
            docs = await self.retrieve_context_documents(
                query, session=session, workspace_id=ws_id, top_k=3
            )

            if not docs:
                # If in cooldown, fast-path to fallback
                if llm_service.is_in_cooldown():
                    logger.info(f"No knowledge context found and in cooldown for workspace {ws_id}. Triggering FallbackService.")
                    fb_result = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name)
                    latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                    return ChatResponse(
                        response=fb_result["response"],
                        citations=[CitationBadge(**c) for c in fb_result["citations"]],
                        latency_ms=latency_ms,
                        confidence=fb_result["confidence"],
                        is_fallback=True,
                        fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN",
                        escalation_recommended=fb_result.get("escalation_recommended", True)
                    )

                # If LLM is healthy, synthesize a polite persona answer rather than leaking unrelated IT FAQs
                logger.info(f"No grounded documents found for workspace {ws_id}. Synthesizing polite persona answer.")
                system_prompt = (
                    f"Bạn là {persona_name}, trợ lý AI đại diện cho doanh nghiệp '{ws_name}' ({industry}).\n"
                    f"Giọng điệu giao tiếp: {tone_of_voice}\n"
                    f"Quy tắc nghiệp vụ bắt buộc:\n{business_rules}\n\n"
                    "Nguyên tắc trả lời nghiêm ngặt (Strict Grounding Rules):\n"
                    "1. Trong cơ sở dữ liệu hiện tại của doanh nghiệp/phòng khám KHÔNG có tài liệu về câu hỏi này.\n"
                    "2. Hãy giải thích lịch sự, nhã nhặn rằng doanh nghiệp/phòng khám hiện chưa có thông tin hoặc không cung cấp dịch vụ liên quan đến câu hỏi này (ví dụ: phòng khám nha khoa không có gói phần mềm hay cam kết SLA phần mềm).\n"
                    "3. Nhắc nhở ngắn gọn về các lĩnh vực/dịch vụ chính mà doanh nghiệp đang hỗ trợ, và hướng dẫn khách hàng bấm nút 'Gửi Ticket' để nhân viên tư vấn hỗ trợ chu đáo nhất."
                )
                user_prompt = (
                    f"Câu hỏi của khách hàng: {query}\n\n"
                    "Hãy trả lời bằng tiếng Việt, lịch sự, đúng phong thái thương hiệu."
                )
                response_text, _ = await llm_service.generate_response(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.2
                )
                total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                return ChatResponse(
                    response=response_text.strip(),
                    citations=[],
                    latency_ms=total_latency_ms,
                    confidence=0.50,
                    is_fallback=False,
                    escalation_recommended=True
                )

            # 2. Synthesize Grounded Context Prompt
            context_blocks: List[str] = []
            citations: List[CitationBadge] = []

            for doc in docs:
                page_info = f" (Trang {doc['page']})" if doc.get("page") else ""
                context_blocks.append(
                    f"--- Nguồn tài liệu: [{doc['doc_id']}] {doc['title']}{page_info} ---\n"
                    f"Nội dung: {doc['content']}"
                )
                citations.append(
                    CitationBadge(
                        doc_id=doc["doc_id"],
                        title=doc["title"],
                        source_url=doc.get("source_url", "/docs"),
                        page=doc.get("page"),
                        snippet=doc.get("snippet")
                    )
                )

            grounded_context = "\n\n".join(context_blocks)
            system_prompt = (
                f"Bạn là {persona_name}, trợ lý AI đại diện cho doanh nghiệp '{ws_name}' ({industry}).\n"
                f"Giọng điệu giao tiếp: {tone_of_voice}\n"
                f"Quy tắc nghiệp vụ bắt buộc:\n{business_rules}\n\n"
                "Nguyên tắc trả lời nghiêm ngặt (Strict Grounding Rules):\n"
                "1. Chỉ trả lời dựa trên Thông tin xác thực trong tài liệu được cung cấp.\n"
                "2. Nếu tài liệu không chứa đủ thông tin để trả lời chính xác, hãy nói rõ là bạn chưa có thông tin và gợi ý khách hàng bấm 'Gửi Ticket' để nhân viên hỗ trợ.\n"
                "3. Tuyệt đối không tự suy diễn hoặc bịa đặt chính sách hay thông số không có trong tài liệu.\n"
                "4. Khi trả lời, hãy đính kèm trích dẫn nguồn nếu phù hợp (ví dụ: [Tên tài liệu - Trang X])."
            )

            user_prompt = (
                f"Câu hỏi của khách hàng: {query}\n\n"
                f"Tài liệu kiến thức đối chiếu:\n{grounded_context}\n\n"
                "Hãy trả lời câu hỏi bằng tiếng Việt, súc tích, chuyên nghiệp và đúng phong cách của doanh nghiệp."
            )

            # 3. Call Google Gemini LLM with hard timeout (4.0s)
            response_text, llm_latency = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
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
            is_cooldown_error = "FREE_TIER_RATE_LIMIT_COOLDOWN" in str(exc)

            logger.warning(
                f"Circuit breaker tripped due to [{type(exc).__name__}: {str(exc)}]. "
                f"Routing immediately to FallbackService..."
            )

            fallback_data = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name)

            return ChatResponse(
                response=fallback_data["response"],
                citations=[CitationBadge(**c) for c in fallback_data["citations"]],
                latency_ms=total_latency_ms,
                confidence=fallback_data["confidence"],
                is_fallback=True,
                fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN" if is_cooldown_error else None,
                escalation_recommended=fallback_data.get("escalation_recommended", True)
            )


rag_service = RAGService()
