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


---

## 2. Task 1 Root Cause Analysis: The 400 INVALID_ARGUMENT Defect & Architectural Fix

### 2.1 Observed Symptom
- When making generation requests to Google Gemini via `llm_service.py`, `gemini-3.5-flash-lite:generateContent` consistently returned `HTTP 400 INVALID_ARGUMENT: Request contains an invalid argument.`.
- This error was improperly classified as a rate limit exception, which immediately triggered the 60-second Cost-Guard cooldown lock (`cooldown_until = now + 60s`), crippling live AI reasoning across the application.
- In contrast, text embeddings via `gemini-embedding-001` consistently returned `200 OK` using the exact same API key, proving that model access, credentials, and network connectivity were completely functional.

### 2.2 Bisect & Reproduction Methodology
A standalone isolation probe (`scratch/gemini_probe.py`) was executed to bisect every parameter constructed by `llm_service.py` against Google GenAI SDK `google-genai 2.24.0`:
1. **Minimal Text Call (`model + contents`):** `200 OK` (Latency: ~720ms).
2. **+ `system_instruction`:** `200 OK`.
3. **+ `temperature: 0.2` & `automatic_function_calling` disable:** `200 OK`.
4. **+ `ThinkingConfig(thinking_budget=0)`:** **FAIL -> `HTTP 400 INVALID_ARGUMENT: Request contains an invalid argument.`**
5. **+ `ThinkingConfig(thinking_level="MINIMAL")`:** **PASS -> `200 OK` (Latency: 710ms).**
6. **Conversation History Edge Cases:**
   - Request whose contents terminated with `role="model"`: **FAIL -> `HTTP 400: Requests ending with a model turn are not supported.`**
   - Request containing `role="system"` inside `contents`: **FAIL -> `HTTP 400: Role 'system' is not supported.`**

### 2.3 Exact Offending Parameter & Architectural Fix
- **Offending Parameter:** `types.ThinkingConfig(thinking_budget=0)` in `backend/app/services/llm_service.py#L279`.
- **Reason:** In Gemini 3.5, Google deprecated integer-based `thinking_budget` in favor of categorical `thinking_level` (`"MINIMAL"`, `"LOW"`, `"MEDIUM"`, `"HIGH"`). Sending `thinking_budget=0` is rejected by the Gemini 3.5 API gateway as an invalid argument.
- **Fix Applied:**
  1. Updated `ThinkingConfig` in `llm_service.py` to:
     ```python
     thinking_level_val = getattr(settings, "GEMINI_THINKING_LEVEL", "MINIMAL") or "MINIMAL"
     thinking_cfg = types.ThinkingConfig(thinking_level=thinking_level_val)
     ```
     Leaving `thinking_budget=None`.
  2. Added `_sanitize_contents()` helper method in `LLMService` that automatically strips any turn with `role="system"` (which must be routed through `config.system_instruction`) and trims trailing `role="model"` turns so generation requests always terminate cleanly on a `user` turn.

---

## 3. Task 2 Error Classification & Circuit Breaker Architecture (Defect C4)

Prior to this fix, all external API exceptions were treated identically, causing client configuration mistakes to lock the entire system in a 60-second cooldown. We implemented strict error classification:

| HTTP Status Code / Error | Classification | Retry Policy | Cooldown Action | Telemetry Status | User Experience |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **400 (INVALID_ARGUMENT)** | Client / Config Error | **0 retries** | **No cooldown** (`0.0s`) | `"config_error"` | Clean fallback to BM25 FAQ matcher |
| **401 / 403 (UNAUTH / PERMISSION)** | Client / Auth Error | **0 retries** | **No cooldown** (`0.0s`) | `"config_error"` | Clean fallback to BM25 FAQ matcher |
| **404 (NOT_FOUND)** | Config / Model Error | Fallback to secondary model if configured, else 0 retries | **No cooldown** (`0.0s`) | `"config_error"` | Clean fallback to BM25 FAQ matcher |
| **429 (RESOURCE_EXHAUSTED)** | Rate Limit / Quota | Honor `Retry-After` if $\le 5.0\text{s}$ (1 retry); else 0 retries | **60s cooldown lock** (`cooldown_until = now + 60s`) | `"fallback"` / `"cooldown"` | BM25 fallback with cooldown notification |
| **500, 502, 503, 504 & Timeout** | Upstream Transient Error | 1 bounded retry (1.0s backoff) | **No cooldown** | `"fallback"` | BM25 fallback with SLA reassurance |

- **API Key Scrubbing:** All error bodies and exception details pass through `scrub_sensitive()` before logging to guarantee API keys (`AIzaSy...`) are never leaked to logs or stdout.
- **Cooldown Reset Endpoint:** `POST /api/v1/agent/ai-usage/reset-cooldown` immediately clears both `llm_service.cooldown_until` and `embedding_service.rate_limited_until`.

---

## 4. Task 4 Verification of Audit Gaps

We added offline test suites in [`backend/tests/ai/test_security_audit_gaps.py`](../../backend/tests/ai/test_security_audit_gaps.py) to formally verify security and isolation guarantees:

1. **Outbound PII Redaction Before External LLM Call:**
   - Verified via `FakeModelsCapturer` that sensitive customer identifiers (emails, phone numbers, CCCD/IDs) are masked with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_ID]` strictly **before** the prompt reaches the Google GenAI SDK.
2. **Two-Phase User Confirmation Lifecycle (`confirm-action`):**
   - Propose stage creates a server-side `PendingAction` with a 30-minute expiration window.
   - Confirming creates exactly one database ticket.
   - Confirming a second time fails with `error_code="ALREADY_EXECUTED"` without creating duplicate tickets.
   - Cancelling marks status `cancelled` and writes zero rows to the database.
   - Expired or unknown action IDs return `ACTION_EXPIRED` (HTTP 400) or `ACTION_NOT_FOUND` (HTTP 404).
   - Cross-user execution is blocked with `ACTION_FORBIDDEN` (HTTP 403) unless the actor holds the `admin` role.
3. **Customer Ticket Scoping:**
   - In `handle_lookup_customer_tickets()`, regular users are strictly constrained to tickets where `Ticket.customer_email.ilike(current_user.email)`. Attempts to search another customer's ticket returns `"Không tìm thấy phiếu hỗ trợ nào"`.
   - Administrators retain global visibility to inspect any ticket across the organization.
4. **Refusal Citation Integrity:**
   - Verified that out-of-scope inquiries (e.g. recipes, cryptocurrency, weather) return polite brand-aligned refusals with `confidence < 0.65`, `escalation_recommended=True`, and **`citations=[]`**, ensuring no unrelated knowledge article is falsely cited.

---

## 5. REQ-16 Multimodal Input Assessment & Recommendation

### 5.1 Requirement Specification
> *"Capability D - Multimodal Input (Conditional on REQ-12 selection): Images, PDFs, or voice are processed by AI (e.g., receipt reading, document extraction, speech-to-text), and the result is stored and used by the app."* (`docs/audit/00-checklist.md:28`, `CRIT-03`, 25% weight).

### 5.2 Current Implementation State
- Document ingestion in [`backend/app/services/document_service.py#L39-L64`](../../backend/app/services/document_service.py) currently parses PDFs using `pypdf.PdfReader`.
- `pypdf` is a non-AI deterministic parser that extracts existing text glyphs from digital text layers.
- When a user uploads a scanned PDF, receipt image, or graphic document without a digital font layer, `document_service.py#L61-L62` explicitly rejects the document with an error:
  `"Tệp PDF scan dạng hình ảnh không chứa text layer. Vui lòng sử dụng tệp PDF chứa văn bản hoặc tệp Markdown / Text."`
- Consequently, Capability D (Multimodal AI) is **only partially satisfied via non-AI methods**.

### 5.3 Proposal Submitted
Because `document_service.py` is owned by Dev B (`@BapVitHoang`), Dev A has formally submitted Change Request [`docs/requests/devA.md`](../requests/devA.md) proposing that Dev B and the Integrator add an AI Vision fallback: when `pypdf` extracts `< 50` characters or when image formats (`.png`, `.jpg`) are uploaded, invoke Gemini 3.5 Flash Lite's native multimodal capabilities (`client.models.generate_content` with `types.Part.from_bytes`) to perform automated OCR before chunking and embedding.
