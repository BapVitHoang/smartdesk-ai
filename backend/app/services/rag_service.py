"""RAG (Retrieval-Augmented Generation) pipeline with Workspace Persona, Agent Tool Routing, SSE Token Streaming, Telemetry Logging, and Cost-Guard Circuit Breaker."""

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR, settings
from app.core.exceptions import LLMServiceException, LLMTimeoutException
from app.core.prompts import prompt_registry
from app.models.document import Document
from app.models.knowledge import FAQItem, KnowledgeChunk
from app.models.workspace import Workspace
from app.schemas.chat import ChatResponse, CitationBadge
from app.services.agent_tools import detect_and_route_tool
from app.services.ai_usage_logger import log_ai_call
from app.services.embedding_service import embedding_service
from app.services.fallback_service import BM25Engine, fallback_service
from app.services.llm_service import llm_service

logger = logging.getLogger("smartdesk.rag")


class RAGService:
    """Orchestrates workspace-aware document retrieval, tool execution, grounded persona prompt synthesis, SSE streaming, and fallback routing."""

    async def _resolve_workspace_persona(
        self,
        session: Optional[AsyncSession],
        ws_id: int,
    ) -> Dict[str, str]:
        """Resolves workspace metadata and persona configuration."""
        persona = {
            "persona_name": "SmartDesk Assistant",
            "ws_name": "SmartDesk Cloud Support",
            "industry": "IT & SaaS",
            "tone_of_voice": "Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật.",
            "business_rules": "Hỗ trợ xử lý sự cố tài khoản, phân quyền, tích hợp API, thanh toán định kỳ. Luôn bảo vệ an toàn thông tin khách hàng.",
        }
        if session:
            try:
                ws_res = await session.execute(select(Workspace).where(Workspace.id == ws_id))
                ws_obj = ws_res.scalar_one_or_none()
                if ws_obj:
                    persona["persona_name"] = ws_obj.persona_name
                    persona["ws_name"] = ws_obj.name
                    persona["industry"] = ws_obj.industry
                    persona["tone_of_voice"] = ws_obj.tone_of_voice
                    persona["business_rules"] = ws_obj.business_rules
            except Exception as e:
                logger.warning(f"Error loading workspace {ws_id}: {e}")
        return persona

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
                min_score = getattr(settings, "RAG_MIN_SIMILARITY_SCORE", 0.25)
                for chk in similar_chunks:
                    chunk_score = chk.get("score", 0.8)
                    if chunk_score < min_score:
                        continue
                    docs.append({
                        "doc_id": chk["chunk_id"],
                        "title": chk["title"],
                        "content": chk["content"],
                        "category": "Workspace Document",
                        "source_url": chk["source_url"],
                        "page": chk.get("page_number", 1),
                        "snippet": chk["content"][:160] + "..." if len(chk["content"]) > 160 else chk["content"],
                        "score": chunk_score
                    })
            except Exception as e:
                logger.warning(f"Workspace chunk retrieval failed: {e}")

        # 2. Hybrid BM25 lexical boost over published workspace chunks (handles pseudo-embedding / offline mode)
        seen_doc_ids = {d["doc_id"] for d in docs}
        if len(docs) < top_k and session:
            try:
                stmt = (
                    select(KnowledgeChunk, Document.status.label("doc_status"))
                    .outerjoin(Document, KnowledgeChunk.document_id == Document.id)
                    .where(KnowledgeChunk.workspace_id == ws_id)
                )
                chunk_rows = (await session.execute(stmt)).all()
                published_chunk_dicts = []
                for chk_obj, doc_status in chunk_rows:
                    if chk_obj.document_id is not None and doc_status != "published":
                        continue
                    published_chunk_dicts.append({
                        "doc_id": chk_obj.chunk_id,
                        "title": chk_obj.title,
                        "content": chk_obj.content,
                        "category": "Workspace Document",
                        "source_url": chk_obj.source_url,
                        "page": chk_obj.page_number or 1,
                        "snippet": chk_obj.content[:160] + "..." if len(chk_obj.content) > 160 else chk_obj.content,
                    })
                if not published_chunk_dicts and ws_id in (2, 3):
                    sample_map = {
                        2: ("Bảng giá Nha Khoa SmileCare", "nha_khoa_smilecare_bang_gia_dich_vu.txt"),
                        3: ("Chính sách đổi trả Điện Máy TechStore", "dien_may_techstore_chinh_sach_doi_tra.txt"),
                    }
                    doc_title, fname = sample_map[ws_id]
                    sample_path = BACKEND_DIR / "data" / "sample_documents" / fname
                    if sample_path.exists():
                        raw_txt = sample_path.read_text(encoding="utf-8")
                        sections = [s.strip() for s in raw_txt.split("\n\n") if len(s.strip()) > 20]
                        for s_idx, sec in enumerate(sections):
                            published_chunk_dicts.append({
                                "doc_id": f"doc-{ws_id}-chk-{s_idx + 1}",
                                "title": f"{doc_title} - Phần {s_idx + 1}",
                                "content": sec,
                                "category": "Workspace Document",
                                "source_url": f"/workspaces/{ws_id}/documents/sample",
                                "page": 1,
                                "snippet": sec[:160] + "..." if len(sec) > 160 else sec,
                            })
                if published_chunk_dicts:
                    bm25_ws = BM25Engine()
                    bm25_ws.fit(published_chunk_dicts)
                    ranked_ws = bm25_ws.score(query)
                    for item_dict, b_score in ranked_ws:
                        if len(docs) >= top_k:
                            break
                        if not b_score or b_score < 1.0:
                            continue
                        if item_dict["doc_id"] not in seen_doc_ids:
                            seen_doc_ids.add(item_dict["doc_id"])
                            item_copy = dict(item_dict)
                            item_copy["score"] = min(0.92, round(0.55 + (b_score / 12.0), 2))
                            docs.append(item_copy)
            except Exception as e:
                logger.warning(f"Hybrid BM25 workspace chunk search failed: {e}")

        # 3. For default workspace, blend with curated FAQ items with deduplication and relevance threshold
        if len(docs) < top_k and ws_id == 1:
            ranked = fallback_service.bm25.score(query)
            if ranked:
                for doc_item, score_val in ranked:
                    if len(docs) >= top_k:
                        break
                    # Require non-trivial BM25 lexical overlap so out-of-scope queries do not pull irrelevant FAQs
                    if not score_val or score_val < 1.2:
                        continue
                    if doc_item["doc_id"] not in seen_doc_ids:
                        seen_doc_ids.add(doc_item["doc_id"])
                        docs.append({
                            "doc_id": doc_item["doc_id"],
                            "title": doc_item["title"],
                            "content": doc_item["content"],
                            "category": doc_item.get("category", "General"),
                            "source_url": doc_item.get("source_url", "/docs"),
                            "page": 1,
                            "snippet": doc_item["content"][:160] + "...",
                            "score": min(0.95, round(0.55 + (score_val / 15.0), 2)),
                        })

        return docs[:top_k]

    async def answer_query(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[int] = None
    ) -> ChatResponse:
        """
        Executes end-to-end RAG query resolution with Agent Tool routing, Workspace Persona, and Cost-Guard Circuit Breaker fallback.
        """
        overall_start = time.perf_counter()
        ws_id = workspace_id or 1
        prompt_ver = prompt_registry.get_prompt_version("rag_customer_support")

        persona = await self._resolve_workspace_persona(session, ws_id)
        persona_name = persona["persona_name"]
        ws_name = persona["ws_name"]
        industry = persona["industry"]
        tone_of_voice = persona["tone_of_voice"]
        business_rules = persona["business_rules"]

        # 0. Single-Pass Agent Tool Router (Capability B - REQ-14)
        try:
            tool_result = await detect_and_route_tool(
                query=query,
                session=session,
                workspace_id=ws_id,
            )
            if tool_result is not None:
                latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                await log_ai_call(
                    endpoint="/api/v1/chat",
                    prompt_version=prompt_ver,
                    provider=llm_service.provider if llm_service.is_available() else "agent_tool_router",
                    model_name=llm_service.active_model_name,
                    tools_called=tool_result["tools_called"],
                    input_tokens=llm_service.estimate_tokens(query),
                    output_tokens=llm_service.estimate_tokens(tool_result["response"]),
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="success",
                    workspace_id=ws_id,
                    session=session,
                )
                return ChatResponse(
                    response=tool_result["response"],
                    citations=[],
                    latency_ms=latency_ms,
                    confidence=tool_result["confidence"],
                    is_fallback=False,
                    escalation_recommended=False,
                    tools_called=tool_result["tools_called"],
                    pending_action=tool_result["pending_action"],
                )
        except Exception as tool_err:
            logger.warning(f"Agent tool routing skipped due to error: {tool_err}")

        # Check if already in Free Tier cooldown
        if llm_service.is_in_cooldown():
            logger.warning("[Cost-Guard] Free Tier cooldown active. Fast-pathing to FallbackService.")
            docs_for_fb = await self.retrieve_context_documents(query, session=session, workspace_id=ws_id, top_k=3)
            fb_result = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name, docs=docs_for_fb)
            latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            await log_ai_call(
                endpoint="/api/v1/chat",
                prompt_version=prompt_ver,
                provider="bm25_fallback",
                model_name="seed_faq_bm25",
                tools_called=[],
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                status="fallback",
                workspace_id=ws_id,
                session=session,
            )
            return ChatResponse(
                response=fb_result["response"],
                citations=[CitationBadge(**c) for c in fb_result["citations"]],
                latency_ms=latency_ms,
                confidence=fb_result["confidence"],
                is_fallback=True,
                fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN",
                escalation_recommended=fb_result.get("escalation_recommended", True),
                tools_called=[],
                pending_action=None,
            )

        docs: List[Dict[str, Any]] = []
        try:
            # 1. Retrieve relevant knowledge context
            docs = await self.retrieve_context_documents(
                query, session=session, workspace_id=ws_id, top_k=3
            )

            if not docs:
                if llm_service.is_in_cooldown():
                    fb_result = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name)
                    latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                    await log_ai_call(
                        endpoint="/api/v1/chat",
                        prompt_version=prompt_ver,
                        provider="bm25_fallback",
                        model_name="seed_faq_bm25",
                        tools_called=[],
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                        latency_ms=latency_ms,
                        status="fallback",
                        workspace_id=ws_id,
                        session=session,
                    )
                    return ChatResponse(
                        response=fb_result["response"],
                        citations=[CitationBadge(**c) for c in fb_result["citations"]],
                        latency_ms=latency_ms,
                        confidence=fb_result["confidence"],
                        is_fallback=True,
                        fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN",
                        escalation_recommended=fb_result.get("escalation_recommended", True),
                        tools_called=[],
                        pending_action=None,
                    )

                # Synthesize polite out-of-scope refusal using externalized prompt
                logger.info(f"No grounded documents found for workspace {ws_id}. Synthesizing polite persona refusal.")
                oos_system_prompt = prompt_registry.render(
                    "rag_out_of_scope_persona",
                    persona_name=persona_name,
                    workspace_name=ws_name,
                    industry=industry,
                    tone_of_voice=tone_of_voice,
                    business_rules=business_rules,
                )
                user_prompt = (
                    f"Câu hỏi của khách hàng: {query}\n\n"
                    "Hãy trả lời bằng tiếng Việt, lịch sự, đúng phong thái thương hiệu."
                )
                response_text, _ = await llm_service.generate_response(
                    prompt=user_prompt,
                    system_prompt=oos_system_prompt,
                    temperature=0.2
                )
                total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
                await log_ai_call(
                    endpoint="/api/v1/chat",
                    prompt_version=prompt_registry.get_prompt_version("rag_out_of_scope_persona"),
                    provider=llm_service.provider,
                    model_name=llm_service.active_model_name,
                    tools_called=[],
                    input_tokens=llm_service.last_input_tokens,
                    output_tokens=llm_service.last_output_tokens,
                    cost_usd=llm_service.last_cost_usd,
                    latency_ms=total_latency_ms,
                    status="refused",
                    workspace_id=ws_id,
                    session=session,
                )
                return ChatResponse(
                    response=response_text.strip(),
                    citations=[],
                    latency_ms=total_latency_ms,
                    confidence=0.45,
                    is_fallback=False,
                    escalation_recommended=True,
                    tools_called=[],
                    pending_action=None,
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
            system_prompt = prompt_registry.render(
                "rag_customer_support",
                persona_name=persona_name,
                workspace_name=ws_name,
                industry=industry,
                tone_of_voice=tone_of_voice,
                business_rules=business_rules,
            )
            user_prompt = prompt_registry.render(
                "rag_user_context",
                query=query,
                grounded_context=grounded_context,
            )

            # 3. Call LLM with hard timeout (4.0s)
            response_text, _ = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )

            total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)

            # Dynamic confidence and refusal detection
            top_score = max((d.get("score", 0.0) for d in docs), default=0.0)
            refusal_keywords = [
                "không có thông tin", "chưa có thông tin", "không thể tìm thấy",
                "không được đề cập", "gửi ticket", "liên hệ bộ phận hỗ trợ",
                "không có trong tài liệu", "không thuộc phạm vi", "tôi không biết"
            ]
            is_refusal = any(kw in response_text.lower() for kw in refusal_keywords) or len(docs) == 0
            confidence = round(top_score, 2) if (top_score > 0 and not is_refusal) else 0.45
            confidence_threshold = getattr(settings, "RAG_CONFIDENCE_THRESHOLD", 0.65)
            escalation_recommended = is_refusal or (confidence < confidence_threshold)

            await log_ai_call(
                endpoint="/api/v1/chat",
                prompt_version=prompt_ver,
                provider=llm_service.provider,
                model_name=llm_service.active_model_name,
                tools_called=[],
                input_tokens=llm_service.last_input_tokens,
                output_tokens=llm_service.last_output_tokens,
                cost_usd=llm_service.last_cost_usd,
                latency_ms=total_latency_ms,
                status="refused" if is_refusal else "success",
                workspace_id=ws_id,
                session=session,
            )

            return ChatResponse(
                response=response_text.strip(),
                citations=citations,
                latency_ms=total_latency_ms,
                confidence=confidence,
                is_fallback=False,
                escalation_recommended=escalation_recommended,
                tools_called=[],
                pending_action=None,
            )

        except (LLMTimeoutException, LLMServiceException, Exception) as exc:
            total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            is_cooldown_error = "FREE_TIER_RATE_LIMIT_COOLDOWN" in str(exc)

            logger.warning(
                f"Circuit breaker tripped due to [{type(exc).__name__}: {str(exc)}]. "
                f"Routing immediately to FallbackService..."
            )

            fallback_data = fallback_service.match_faq(query, workspace_id=ws_id, workspace_name=ws_name, docs=docs)

            await log_ai_call(
                endpoint="/api/v1/chat",
                prompt_version=prompt_ver,
                provider="bm25_fallback",
                model_name="seed_faq_bm25",
                tools_called=[],
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=total_latency_ms,
                status="fallback",
                workspace_id=ws_id,
                session=session,
            )

            return ChatResponse(
                response=fallback_data["response"],
                citations=[CitationBadge(**c) for c in fallback_data["citations"]],
                latency_ms=total_latency_ms,
                confidence=fallback_data["confidence"],
                is_fallback=True,
                fallback_reason="FREE_TIER_RATE_LIMIT_COOLDOWN" if is_cooldown_error else None,
                escalation_recommended=fallback_data.get("escalation_recommended", True),
                tools_called=[],
                pending_action=None,
            )

    async def answer_query_stream(
        self,
        query: str,
        session: Optional[AsyncSession] = None,
        workspace_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams RAG response token-by-token via Server-Sent Events (SSE - REQ-04, REQ-10).
        Emits `metadata`, `token`, and `done` events compatible with both CONTRACTS.md §8.3 and frontend streamChatMessage().
        """
        chat_res = await self.answer_query(query=query, session=session, workspace_id=workspace_id)
        citations_dicts = [c.model_dump() for c in chat_res.citations]
        pending_dict = chat_res.pending_action.model_dump() if chat_res.pending_action else None

        meta_payload = {
            "type": "metadata",
            "session_id": session_id or "sess-stream",
            "model": llm_service.active_model_name if not chat_res.is_fallback else "seed_faq_bm25",
            "prompt_version": f"v{prompt_registry.version}",
            "citations": citations_dicts,
            "confidence": chat_res.confidence,
            "is_fallback": chat_res.is_fallback,
            "escalation_recommended": chat_res.escalation_recommended,
            "tools_called": chat_res.tools_called,
            "pending_action": pending_dict,
        }
        yield f"event: metadata\ndata: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"

        words = chat_res.response.split(" ")
        for idx, word in enumerate(words):
            chunk_str = f"{word}{' ' if idx < len(words) - 1 else ''}"
            token_payload = {
                "type": "token",
                "token": chunk_str,
                "delta": chunk_str,
            }
            yield f"event: token\ndata: {json.dumps(token_payload, ensure_ascii=False)}\n\n"

        done_payload = {
            "type": "done",
            "done": True,
            "response": chat_res.response,
            "citations": citations_dicts,
            "latency_ms": chat_res.latency_ms,
            "confidence": chat_res.confidence,
            "is_fallback": chat_res.is_fallback,
            "fallback_reason": chat_res.fallback_reason,
            "escalation_recommended": chat_res.escalation_recommended,
            "pending_action": pending_dict,
            "tools_called": chat_res.tools_called,
            "prompt_version": prompt_registry.get_prompt_version("rag_customer_support"),
        }
        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


rag_service = RAGService()
