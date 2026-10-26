# Developer A — AI Usage & Prompting Log (`A-ai-usage.md`)

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session for Workstream A is recorded below, including real bugs encountered and how they were fixed.

---

### Session 1: Single-Call Pydantic v2 Structured Output (`ticket_copilot_service.py` & `llm_service.py`)
- **Date:** 2026-10-21
- **AI Tool Used:** Google Antigravity Coding Assistant
- **Key Prompt:** *"Implement `generate_structured_output()` in `llm_service.py` and `generate_ticket_triage_and_draft()` in `ticket_copilot_service.py` adhering to `CONTRACTS.md` §4 & §7, normalizing `'Technical Bug'` to `'Bug Report'` and providing a deterministic Vietnamese fallback when Gemini is in cooldown."*
- **Manual Verification & Changes:**
  - Verified `TicketCopilotStructuredOutput` field constraints (`min_length`, `max_length`, `Literal` enums) and tested alias normalization with `pytest backend/tests/test_rag_module.py`.
- **AI Mistakes & Corrections:**
  - *Observed Issue:* The initial stub in `llm_service.py#L269` caught `Exception` on `model_validate_json()` and silently returned `response_model.model_construct()` (an empty unvalidated Pydantic object with missing required fields), which would cause downstream `AttributeError` in `ticket_copilot_service.py`.
  - *Commit Hash / File:* Fixed on base commit `c10cf89` in `backend/app/services/llm_service.py#L254-L272`.
  - *Fix Applied:* Replaced `model_construct()` fallback with markdown fence stripping (`_extract_json_payload`) and explicit `LLMServiceException` raising so `ticket_copilot_service.py` cleanly invokes its deterministic Vietnamese fallback builder.

---

### Session 2: 4-Tool Agent Registry & Two-Phase User Confirmation (`agent_tools.py` & `chat_actions.py`)
- **Date:** 2026-10-21
- **AI Tool Used:** Google Antigravity Coding Assistant
- **Key Prompt:** *"Implement 4 DB-backed support tools in `backend/app/services/agent_tools.py` (`lookup_customer_tickets`, `search_workspace_knowledge`, `create_escalation_ticket`, `update_ticket_priority_or_status`) and wire two-phase confirmation in `chat_actions.py`."*
- **Manual Verification & Changes:**
  - Ran `python backend/scripts/run_eval.py --mode deterministic` and `pytest backend/tests/ai/test_dev_a_suite.py` to test read-only ticket lookup (`#TICK-1042`) and mutating confirmation cards (`act-...`).
- **AI Mistakes & Corrections:**
  - *Observed Issue:* Initial AI-generated code in `agent_tools.py` referenced `ticket.sla_hours` on the SQLAlchemy `Ticket` model, causing `AttributeError: 'Ticket' object has no attribute 'sla_hours'` during `EVAL-09` execution because the ORM column in `backend/app/models/ticket.py#L41` is named `estimated_response_hours`.
  - *Commit Hash / File:* Diagnosed during benchmark run on base commit `c10cf89` in `backend/app/services/agent_tools.py#L148-L270`.
  - *Fix Applied:* Updated `agent_tools.py` to read and write `estimated_response_hours` on `Ticket` ORM instances while mapping it to `sla_hours` in the tool output dictionary.

---

### Session 3: 24-Case Evaluation Benchmark & Hybrid BM25 Chunk Retrieval (`run_eval.py` & `rag_service.py`)
- **Date:** 2026-10-21
- **AI Tool Used:** Google Antigravity Coding Assistant
- **Key Prompt:** *"Create `backend/data/eval_dataset.json` (24 cases: 10 normal, 6 edge, 8 should-refuse across Workspaces 1–3) and `backend/scripts/run_eval.py` comparing Legacy Baseline vs Upgraded Pipeline."*
- **Manual Verification & Changes:**
  - Verified all 24 cases against actual sample document contents (`nha_khoa_smilecare_bang_gia_dich_vu.txt` and `dien_may_techstore_chinh_sach_doi_tra.txt`).
- **AI Mistakes & Corrections:**
  - *Observed Issue:*
    1. In `run_eval.py`, setting only `llm_service.cooldown_until` left `embedding_service` attempting live Gemini API calls (`rate_limited_until` was the actual attribute name in `EmbeddingService`, not `cooldown_until`).
    2. When `KnowledgeChunk` records used SHA-256 pseudo-embeddings in offline/deterministic mode, cosine similarity between query and chunk pseudo-vectors was `< 0.25`, causing Workspace 2 & 3 queries (`EVAL-06..08`) to return empty context.
  - *Commit Hash / File:* Fixed on base commit `c10cf89` in `backend/scripts/run_eval.py#L228` and `backend/app/services/rag_service.py#L97-L145`.
  - *Fix Applied:* Fixed `embedding_service.rate_limited_until` in `llm_service.py` and `run_eval.py`, and added a hybrid BM25 lexical boost over published workspace chunks in `rag_service.retrieve_context_documents()`.

---

### Session 4: Gemini 3.5 400 INVALID_ARGUMENT Root Cause Fix, Circuit Breaker & Audit Gaps (`llm_service.py`, `rag_service.py`, `agent_tools.py`)
- **Date:** 2026-10-23
- **AI Tool Used:** Google Antigravity Coding Assistant
- **Key Prompt:** *"Investigate live generateContent 400 INVALID_ARGUMENT on gemini-3.5-flash-lite, bisect SDK parameters, classify errors (400/401/403/404 as config_error with 0 retries and 0 cooldown, 429 with Retry-After, 5xx with limited retry), address audit gaps (PII redaction before LLM call, two-phase confirmation lifecycle, customer ticket scoping, refusal citations), and run live evaluation."*
- **Manual Verification & Changes:**
  - Ran live parameter bisect on `google-genai 2.24.0` against model `gemini-3.5-flash-lite`.
  - Proved root cause: Gemini 3.5 rejects `thinking_budget` in `ThinkingConfig` with `400 INVALID_ARGUMENT`. Replaced with `types.ThinkingConfig(thinking_level="MINIMAL")` and verified live with 200 OK (< 1,500ms latency).
  - Executed 4 live calls (grounded RAG, structured ticket copilot, tool routing, SSE streaming) and verified real latency/tokens in telemetry.
  - Added unit test suites `backend/tests/ai/test_llm_request_and_circuit_breaker.py` and `backend/tests/ai/test_security_audit_gaps.py` (34/34 tests passing across full Dev A suite).
- **AI Mistakes & Corrections:**
  - *Observed Issue 1 (Fixture Error):* Initial code for `test_security_audit_gaps.py` declared `db_session` as a test parameter expecting it from `conftest.py`, causing `fixture 'db_session' not found` across 5 database tests.
    - *Commit / File:* `backend/tests/ai/test_security_audit_gaps.py#L25`.
    - *Fix Applied:* Defined a local `@pytest_asyncio.fixture async def db_session()` yielding from `session_module.async_session_factory()`, adhering strictly to module boundaries without touching frozen `conftest.py`.
  - *Observed Issue 2 (Windows Console Encoding):* `scratch/live_verify.py` crashed on Windows console with `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ea1' (cp1252)` when printing Vietnamese response text.
    - *Commit / File:* `scratch/live_verify.py#L9-L16`.
    - *Fix Applied:* Added `sys.stdout.reconfigure(encoding="utf-8")` and `sys.stderr.reconfigure(encoding="utf-8")` at script startup.
  - *Observed Issue 3 (Circuit Breaker Reason):* `rag_service.py` initially caught `LLMConfigException` under generic `except Exception`, returning `fallback_reason = None` instead of `"CONFIG_ERROR"`, which caused `test_rag_fallback_on_llm_config_error_records_telemetry_status` to fail.
    - *Commit / File:* `backend/app/services/rag_service.py#L436-L470`.
    - *Fix Applied:* Added explicit `is_config_error` branch setting `fallback_reason = "CONFIG_ERROR"` and recording telemetry `status = "config_error"`.
