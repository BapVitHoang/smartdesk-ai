"""Active Knowledge Verification Engine with Parallel Synthetic QA, RAG Self-Test, AI Judge Structured Output, and Multi-Agent Trace (Capabilities C & E)."""

import asyncio
import datetime
import json
import logging
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import prompt_registry
from app.models.document import Document
from app.models.knowledge import KnowledgeChunk
from app.models.verification import VerificationItem, VerificationReport
from app.models.workspace import Workspace
from app.schemas.ai_structured import (
    AgentHandOffStep,
    FaithfulnessJudgeStructuredOutput,
)
from app.services.ai_usage_logger import log_ai_call
from app.services.llm_service import llm_service

logger = logging.getLogger("smartdesk.verification")


class VerificationService:
    """Orchestrates 3-step active verification: SyntheticQAExamAgent -> SandboxRAGAgent -> FaithfulnessJudgeAgent."""

    def __init__(self) -> None:
        self._trace_cache: Dict[int, List[AgentHandOffStep]] = {}

    def get_agent_trace(
        self,
        document_id: int,
        faithfulness_score: float = 0.90,
        status: str = "passed",
        item_count: int = 3,
    ) -> List[AgentHandOffStep]:
        """Returns the hand-off trace recorded by the last verification run in this process ([] if none)."""
        return list(self._trace_cache.get(document_id, []))

    @staticmethod
    def load_agent_trace(
        report: Optional[VerificationReport],
    ) -> List[AgentHandOffStep]:
        """Parses the hand-off trace persisted on a VerificationReport row."""
        raw = getattr(report, "agent_trace_json", None) if report is not None else None
        if not raw:
            return []
        try:
            return [AgentHandOffStep.model_validate(step) for step in json.loads(raw)]
        except Exception as exc:
            logger.warning(
                f"Invalid agent_trace_json on report {getattr(report, 'id', '?')}: {exc}"
            )
            return []

    @staticmethod
    def clean_json_response(raw_text: str) -> Any:
        """
        Safely extracts and parses JSON payload even when Gemini wraps output in markdown code blocks.
        Falls back gracefully if parsing fails.
        """
        if not raw_text or not raw_text.strip():
            return {
                "score": 0.0,
                "status": "failed",
                "reason": "Không nhận được phản hồi đánh giá từ bộ máy suy luận.",
            }

        text = raw_text.strip()

        # 1. Try stripping markdown code fences: ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # 2. Try matching outer [...] or {...}
        arr_match = re.search(r"(\[[\s\S]*\])", text)
        obj_match = re.search(r"(\{[\s\S]*\})", text)
        if arr_match and (not obj_match or arr_match.start() < obj_match.start()):
            try:
                return json.loads(arr_match.group(1))
            except Exception:
                pass
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except Exception:
                pass

        # 3. Direct json.loads attempt
        try:
            return json.loads(text)
        except Exception:
            logger.warning(
                f"Could not parse JSON from LLM response: {text[:100]}... Verification failed."
            )
            return {
                "score": 0.0,
                "status": "failed",
                "reason": "Không thể phân tích cấu trúc JSON từ kết quả đánh giá của AI Judge.",
            }

    async def generate_synthetic_qa(
        self, chunks: List[KnowledgeChunk]
    ) -> List[Dict[str, str]]:
        """
        SyntheticQAExamAgent: Generates 3 synthetic test QA pairs based on knowledge chunks.
        Falls back to rule-based questions if LLM is offline or rate limited.
        """
        if not chunks:
            return []

        from app.services.embedding_service import embedding_service

        if (
            embedding_service.is_rate_limited()
            or llm_service.is_in_cooldown()
            or not llm_service.is_available()
        ):
            return self._generate_rule_based_qa(chunks)

        selected_chunks = chunks[:3]
        context_text = "\n\n".join(
            [f"Đoạn {i+1}: {c.content}" for i, c in enumerate(selected_chunks)]
        )

        prompt = prompt_registry.render(
            "verification_synthetic_qa", context_text=context_text
        )

        try:
            response_text, _ = await llm_service.generate_response(
                prompt=prompt, temperature=0.2
            )
            cleaned = self.clean_json_response(response_text)
            if isinstance(cleaned, list) and len(cleaned) > 0:
                qa_list: List[Dict[str, str]] = []
                for item in cleaned:
                    if (
                        isinstance(item, dict)
                        and "question" in item
                        and "ground_truth" in item
                    ):
                        qa_list.append(
                            {
                                "question": str(item["question"]),
                                "ground_truth": str(item["ground_truth"]),
                            }
                        )
                if qa_list:
                    return qa_list[:3]
        except Exception as e:
            logger.warning(
                f"Synthetic QA generation via LLM failed: {e}. Using deterministic fallback QA."
            )

        return self._generate_rule_based_qa(chunks)

    def _generate_rule_based_qa(
        self, chunks: List[KnowledgeChunk]
    ) -> List[Dict[str, str]]:
        """Generates deterministic QA pairs directly extracted from chunk sentences."""
        qa_list: List[Dict[str, str]] = []
        for chunk in chunks[:3]:
            sentences = [
                s.strip()
                for s in re.split(r"[.!?\n]", chunk.content)
                if len(s.strip()) > 15
            ]
            first_sentence = sentences[0] if sentences else chunk.content[:100]
            second_sentence = sentences[1] if len(sentences) > 1 else first_sentence

            qa_list.append(
                {
                    "question": f"Thông tin chính được nêu trong {chunk.title} là gì?",
                    "ground_truth": f"{first_sentence}. {second_sentence}",
                }
            )
        return qa_list

    async def evaluate_faithfulness(
        self, ground_truth: str, rag_answer: str
    ) -> Tuple[float, str, str]:
        """
        FaithfulnessJudgeAgent: Evaluates semantic faithfulness between Ground Truth and RAG Answer
        using Pydantic Structured Output (FaithfulnessJudgeStructuredOutput).
        Returns: (score [0.0 - 1.0], status ['passed' | 'warning' | 'failed'], reason)
        """
        from app.services.embedding_service import embedding_service

        if (
            embedding_service.is_rate_limited()
            or llm_service.is_in_cooldown()
            or not llm_service.is_available()
        ):
            return self._deterministic_judge(ground_truth, rag_answer)

        judge_prompt = prompt_registry.render(
            "verification_ai_judge",
            ground_truth=ground_truth,
            rag_answer=rag_answer,
        )

        try:
            # First try structured output validation against FaithfulnessJudgeStructuredOutput
            try:
                structured_judgment, _ = await llm_service.generate_structured_output(
                    prompt=judge_prompt,
                    response_model=FaithfulnessJudgeStructuredOutput,
                    temperature=0.1,
                )
                score = round(max(0.0, min(1.0, float(structured_judgment.score))), 2)
                if score >= 0.85:
                    status_str = "passed"
                elif score >= 0.60:
                    status_str = "warning"
                else:
                    status_str = "failed"
                return score, status_str, structured_judgment.reason
            except Exception:
                response_text, _ = await llm_service.generate_response(
                    prompt=judge_prompt, temperature=0.1
                )
                data = self.clean_json_response(response_text)
                if not isinstance(data, dict):
                    return self._deterministic_judge(ground_truth, rag_answer)
                score = float(data.get("score", 0.85))
                score = max(0.0, min(1.0, score))

                if score >= 0.85:
                    status_str = "passed"
                elif score >= 0.60:
                    status_str = "warning"
                else:
                    status_str = "failed"

                reason = str(
                    data.get(
                        "reason",
                        "Câu trả lời đạt độ chính xác theo tiêu chuẩn thẩm định.",
                    )
                )
                return score, status_str, reason
        except Exception as e:
            logger.warning(
                f"AI Judge evaluation failed: {e}. Using deterministic score."
            )
            return self._deterministic_judge(ground_truth, rag_answer)

    def _deterministic_judge(
        self, ground_truth: str, rag_answer: str
    ) -> Tuple[float, str, str]:
        """Calculates token overlap ratio as deterministic judge fallback."""
        gt_tokens = set(re.findall(r"\w+", ground_truth.lower()))
        rag_tokens = set(re.findall(r"\w+", rag_answer.lower()))

        if not gt_tokens or not rag_tokens:
            return 0.30, "failed", "Dữ liệu đối soát không đủ token để thẩm định."

        overlap = len(gt_tokens.intersection(rag_tokens))
        ratio = overlap / len(gt_tokens)

        score = round(min(0.95, ratio), 2)
        if score >= 0.70:
            status_str = "passed"
        elif score >= 0.40:
            status_str = "warning"
        else:
            status_str = "failed"

        reason = f"Đối soát tự động nội bộ: Độ khớp từ vựng đạt {int(ratio * 100)}%."
        return score, status_str, reason

    def _rank_chunks_for_query(
        self,
        query: str,
        chunks: List[KnowledgeChunk],
        query_vector: Optional[List[float]] = None,
    ) -> List[KnowledgeChunk]:
        """Ranks document chunks by semantic/keyword relevance specifically for the verification sandbox."""
        if not chunks:
            return []

        if query_vector:
            scored = []
            for chk in chunks:
                emb = chk.embedding
                if isinstance(emb, str):
                    try:
                        emb = json.loads(emb)
                    except Exception:
                        emb = None
                if emb and isinstance(emb, list) and len(emb) == len(query_vector):
                    dot = sum(a * b for a, b in zip(query_vector, emb))
                    norm_a = math.sqrt(sum(a * a for a in query_vector))
                    norm_b = math.sqrt(sum(b * b for b in emb))
                    sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
                    scored.append((chk, sim))
                else:
                    scored.append((chk, 0.0))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [x[0] for x in scored[:3]]

        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for chk in chunks:
            c_tokens = set(re.findall(r"\w+", chk.content.lower()))
            overlap = len(q_tokens.intersection(c_tokens))
            scored.append((chk, overlap))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in scored[:3]]

    async def answer_sandbox_query(
        self,
        query: str,
        chunks: List[KnowledgeChunk],
        workspace_name: str = "Doanh nghiệp",
    ) -> str:
        """
        SandboxRAGAgent: Evaluates RAG retrieval and synthesis directly on the Document Under Test (DUT).
        Completely decoupled from the Customer-facing Production Chatbot.
        """
        from app.services.embedding_service import embedding_service

        query_vec = None
        try:
            if not embedding_service.is_rate_limited():
                query_vec = await embedding_service.get_text_embedding(query)
        except Exception as e:
            logger.debug(f"Query embedding for sandbox test skipped: {e}")

        top_chunks = self._rank_chunks_for_query(query, chunks, query_vec)
        if not top_chunks:
            top_chunks = chunks[:3]

        context_blocks = [
            f"[Đoạn {chk.chunk_index + 1} - Trang {chk.page_number}]:\n{chk.content}"
            for chk in top_chunks
        ]
        context_str = "\n\n".join(context_blocks)

        prompt = prompt_registry.render(
            "verification_sandbox_rag",
            workspace_name=workspace_name,
            context_str=context_str,
            query=query,
        )

        try:
            if not llm_service.is_in_cooldown() and llm_service.is_available():
                resp, _ = await llm_service.generate_response(
                    prompt=prompt, temperature=0.1
                )
                return resp.strip()
        except Exception as e:
            logger.warning(f"Sandbox LLM answer generation failed: {e}")

        return top_chunks[0].content

    async def verify_document(
        self, document_id: int, session: AsyncSession
    ) -> VerificationReport:
        """
        Executes full 3-Agent verification pipeline in an ISOLATED SANDBOX (Capability E - REQ-17):
        1. SyntheticQAExamAgent: Generate synthetic QA pairs from document chunks
        2. SandboxRAGAgent: Run RAG sandbox test on Document Under Test (DUT) in PARALLEL via asyncio.gather()
        3. FaithfulnessJudgeAgent: Run AI Judge faithfulness evaluations
        4. Record multi-agent hand-off trace (`agent_trace`) and persist report to DB
        """
        doc_result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Không tìm thấy tài liệu ID {document_id}")

        chunk_result = await session.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()
        if not chunks:
            raise ValueError(f"Tài liệu {document_id} chưa có đoạn dữ liệu (chunks).")

        doc.status = "processing"
        await session.commit()

        start_time = time.perf_counter()
        trace_steps: List[AgentHandOffStep] = []

        try:
            # Step 1: SyntheticQAExamAgent
            t1_start = time.perf_counter()
            qa_pairs = await self.generate_synthetic_qa(list(chunks))
            if not qa_pairs:
                qa_pairs = self._generate_rule_based_qa(list(chunks))
            t1_ms = round((time.perf_counter() - t1_start) * 1000, 2)
            trace_steps.append(
                AgentHandOffStep(
                    step_order=1,
                    agent="SyntheticQAExamAgent",
                    from_agent="DocumentIngestionPipeline",
                    to_agent="SyntheticQAExamAgent",
                    action="generate_evaluation_questions",
                    input_summary=f"{len(chunks)} document chunks ({doc.filename})",
                    output_summary=f"{len(qa_pairs)} synthetic QA pairs generated",
                    latency_ms=t1_ms,
                    status="success",
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )

            # Step 2: SandboxRAGAgent (Parallel execution via asyncio.gather)
            t2_start = time.perf_counter()
            questions = [qa["question"] for qa in qa_pairs]
            ws_name = "Doanh nghiệp"
            if doc.workspace_id:
                ws_res = await session.execute(
                    select(Workspace).where(Workspace.id == doc.workspace_id)
                )
                ws_obj = ws_res.scalar_one_or_none()
                if ws_obj:
                    ws_name = ws_obj.name

            rag_tasks = [
                self.answer_sandbox_query(
                    query=q, chunks=list(chunks), workspace_name=ws_name
                )
                for q in questions
            ]
            rag_answers = await asyncio.gather(*rag_tasks)
            t2_ms = round((time.perf_counter() - t2_start) * 1000, 2)
            trace_steps.append(
                AgentHandOffStep(
                    step_order=2,
                    agent="SandboxRAGAgent",
                    from_agent="SyntheticQAExamAgent",
                    to_agent="SandboxRAGAgent",
                    action="answer_synthetic_questions",
                    input_summary=f"{len(questions)} synthetic questions",
                    output_summary=f"{len(rag_answers)} answers retrieved and generated in parallel",
                    latency_ms=t2_ms,
                    status="success",
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )

            # Step 3: FaithfulnessJudgeAgent
            t3_start = time.perf_counter()
            judge_tasks = [
                self.evaluate_faithfulness(qa["ground_truth"], rag_ans)
                for qa, rag_ans in zip(qa_pairs, rag_answers)
            ]
            judge_results = await asyncio.gather(*judge_tasks)
            t3_ms = round((time.perf_counter() - t3_start) * 1000, 2)

            # Compile Verification Items & Report
            total_score = 0.0
            has_failed = False
            has_warning = False

            existing_report_res = await session.execute(
                select(VerificationReport).where(
                    VerificationReport.document_id == document_id
                )
            )
            existing_report = existing_report_res.scalar_one_or_none()
            if existing_report:
                from sqlalchemy import delete

                await session.execute(
                    delete(VerificationItem).where(
                        VerificationItem.report_id == existing_report.id
                    )
                )
                await session.delete(existing_report)
                await session.flush()

            report = VerificationReport(
                document_id=doc.id,
                workspace_id=doc.workspace_id,
                faithfulness_score=0.0,
                status="passed",
            )
            session.add(report)
            await session.flush()

            for qa, rag_ans, (score, status_str, reason) in zip(
                qa_pairs, rag_answers, judge_results
            ):
                total_score += score
                if status_str == "failed":
                    has_failed = True
                elif status_str == "warning":
                    has_warning = True

                item = VerificationItem(
                    report_id=report.id,
                    question=qa["question"],
                    ground_truth=qa["ground_truth"],
                    rag_answer=rag_ans,
                    score=score,
                    status=status_str,
                    reason=reason,
                )
                session.add(item)

            avg_score = round(total_score / max(1, len(qa_pairs)), 2)
            report.faithfulness_score = avg_score

            if has_failed or avg_score < 0.60:
                report.status = "failed"
                doc.status = "failed"
            elif has_warning or avg_score < 0.85:
                report.status = "warning"
                doc.status = "verified"
            else:
                report.status = "passed"
                doc.status = "verified"

            trace_steps.append(
                AgentHandOffStep(
                    step_order=3,
                    agent="FaithfulnessJudgeAgent",
                    from_agent="SandboxRAGAgent",
                    to_agent="FaithfulnessJudgeAgent",
                    action="evaluate_faithfulness",
                    input_summary=f"{len(qa_pairs)} RAG answers vs ground truth",
                    output_summary=f"Faithfulness score: {avg_score} ({report.status})",
                    latency_ms=t3_ms,
                    status="success" if report.status != "failed" else "failed",
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
            )
            self._trace_cache[doc.id] = trace_steps
            report.agent_trace_json = json.dumps(
                [s.model_dump() for s in trace_steps], ensure_ascii=False
            )
            for step in trace_steps:
                logger.info(
                    f"[AgentHandOff] doc={doc.id} step={step.step_order} {step.from_agent} -> {step.to_agent} "
                    f"action={step.action} status={step.status} latency={step.latency_ms}ms output='{step.output_summary}'"
                )

            await session.commit()
            await session.refresh(report)
            setattr(report, "agent_trace", trace_steps)

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            used_live_llm = (
                llm_service.is_available() and not llm_service.is_in_cooldown()
            )
            await log_ai_call(
                endpoint="/api/v1/documents/verify",
                prompt_version=prompt_registry.get_prompt_version(
                    "verification_ai_judge"
                ),
                provider=llm_service.provider if used_live_llm else "bm25_fallback",
                model_name=(
                    llm_service.active_model_name
                    if used_live_llm
                    else "deterministic-judge-v2"
                ),
                tools_called=[
                    "SyntheticQAExamAgent",
                    "SandboxRAGAgent",
                    "FaithfulnessJudgeAgent",
                ],
                input_tokens=llm_service.last_input_tokens if used_live_llm else 0,
                output_tokens=llm_service.last_output_tokens if used_live_llm else 0,
                cost_usd=llm_service.last_cost_usd if used_live_llm else 0.0,
                latency_ms=elapsed_ms,
                status="success" if used_live_llm else "fallback",
                workspace_id=doc.workspace_id or 1,
                session=session,
            )

            logger.info(
                f"Completed 3-agent active verification for Document {doc.id} in {round(elapsed_ms / 1000, 2)}s: "
                f"Score={avg_score}, Status={report.status}"
            )
            return report
        except Exception as exc:
            logger.error(
                f"Active verification failed for Document {doc.id}: {exc}",
                exc_info=True,
            )
            doc.status = "failed"
            try:
                await session.commit()
            except Exception:
                await session.rollback()
            raise

    async def publish_document(
        self, document_id: int, session: AsyncSession
    ) -> Document:
        """
        Activates document into the live knowledge base (status = 'published').
        Requires document to have passed verification (status == 'verified').
        """
        doc_result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Không tìm thấy tài liệu ID {document_id}")

        if doc.status != "verified":
            raise ValueError(
                f"Tài liệu ID {document_id} chưa đạt kiểm định (trạng thái hiện tại: '{doc.status}'). "
                f"Chỉ tài liệu đã qua sát hạch thành công ('verified') mới được xuất bản vào RAG."
            )

        doc.status = "published"
        await session.commit()
        await session.refresh(doc)
        logger.info(f"Published document ID {document_id} to active knowledge base.")
        return doc


verification_service = VerificationService()
