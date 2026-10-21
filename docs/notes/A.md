# Developer A — Technical Notes & Architecture Decisions (`A.md`)

> **Workstream:** AI Engine, RAG Pipeline, Structured Output, Tool-Using Agent, SSE Streaming & Evaluation (`feature/a-ai-engine`)  
> **Owner:** Developer A (`@TheOrijinnn`)

---

## 1. Completed Deliverables Summary

1. **Externalized Hot-Reloading Prompt Catalog (`TASK-04` / `REQ-19`):**
   - Externalized all 8 prompt templates (`rag_customer_support`, `rag_out_of_scope_persona`, `rag_user_context`, `ticket_copilot_structured`, `ticket_copilot_draft`, `verification_synthetic_qa`, `verification_sandbox_rag`, `verification_ai_judge`) into [`backend/data/prompts.json`](../../backend/data/prompts.json).
   - Added automatic file `mtime` hot-reload detection in [`backend/app/core/prompts.py`](../../backend/app/core/prompts.py) so prompt edits during the 10-minute Live Change Defense apply immediately without server restarts.
2. **Capability C — Single-Call Pydantic v2 Structured Output (`TASK-08` / `REQ-15`):**
   - Defined `TicketCopilotStructuredOutput` (with `@field_validator` normalizing `"Technical Bug"` to `"Bug Report"`) and `FaithfulnessJudgeStructuredOutput` in [`backend/app/schemas/ai_structured.py`](../../backend/app/schemas/ai_structured.py).
   - Implemented `LLMService.generate_structured_output()` in [`backend/app/services/llm_service.py`](../../backend/app/services/llm_service.py) supporting Gemini native `response_schema` and Ollama JSON mode.
   - Created [`backend/app/services/ticket_copilot_service.py`](../../backend/app/services/ticket_copilot_service.py) (`generate_ticket_triage_and_draft`) to perform ticket classification, priority estimation, tag extraction, sentiment analysis, concise summarization, and localized Vietnamese draft generation in **a single LLM call**, with deterministic fallback when offline or rate-limited.
3. **Capability E — 3-Agent Active Verification Hand-Off Trace (`TASK-08` / `REQ-17`):**
   - Instrumented [`backend/app/services/verification_service.py`](../../backend/app/services/verification_service.py) and [`backend/app/schemas/verification.py`](../../backend/app/schemas/verification.py) to record and return structured `agent_trace` steps across `SyntheticQAExamAgent` $\to$ `SandboxRAGAgent` $\to$ `FaithfulnessJudgeAgent`.
4. **Capability B — 4 DB-Backed Agent Tools & Two-Phase User Confirmation (`TASK-09` / `REQ-14`):**
   - Implemented 4 tools in [`backend/app/services/agent_tools.py`](../../backend/app/services/agent_tools.py):
     1. `lookup_customer_tickets` (read-only DB lookup by `#TICK-XXXX` or `customer_email`).
     2. `search_workspace_knowledge` (read-only workspace chunk & FAQ search).
     3. `create_escalation_ticket` (`requires_confirmation=True`, stores `PendingActionSchema` until confirmed).
     4. `update_ticket_priority_or_status` (`requires_confirmation=True`, stores `PendingActionSchema` until confirmed).
   - Wired `POST /api/v1/chat/confirm-action` in [`backend/app/api/v1/endpoints/chat_actions.py`](../../backend/app/api/v1/endpoints/chat_actions.py) to execute confirmed actions against SQLAlchemy `AsyncSession`.
5. **SSE Token-by-Token Streaming & AI Observability (`TASK-10`, `TASK-11` / `REQ-04`, `REQ-10`, `REQ-22`, `REQ-33`):**
   - Implemented `rag_service.answer_query_stream()` and `POST /api/v1/chat/stream` in [`backend/app/api/v1/endpoints/chat_stream.py`](../../backend/app/api/v1/endpoints/chat_stream.py) emitting `metadata`, `token`, and `done` SSE events.
   - Wired automatic `log_ai_call()` telemetry across `rag_service.py`, `chat.py`, `chat_stream.py`, `ticket_copilot_service.py`, and `verification_service.py`, plus `GET /api/v1/agent/ai-usage` and `POST /api/v1/agent/ai-usage/reset-cooldown` in [`backend/app/api/v1/endpoints/ai_usage.py`](../../backend/app/api/v1/endpoints/ai_usage.py).
6. **24-Case AI Evaluation Benchmark (`TASK-15` / `REQ-21`):**
   - Created [`backend/data/eval_dataset.json`](../../backend/data/eval_dataset.json) (10 normal, 6 edge, 8 should-refuse cases) and [`backend/scripts/run_eval.py`](../../backend/scripts/run_eval.py), improving measured pass rate from **33.3% (8/24)** on the legacy baseline to **100.0% (24/24)** on the upgraded pipeline.
