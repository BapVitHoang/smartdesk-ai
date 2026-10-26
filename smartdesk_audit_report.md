# SmartDesk AI — Technical Audit & Upgrade Plan

> **Audit date:** 2026-10-08 · **Commit:** `ff3db92` (+ untracked `backend/PYTHON_FILES_EXPLANATION.md`)
> **Mode:** read-only. No project files were changed. I ran the test suite against a throwaway SQLite DB in the scratch folder with `GEMINI_API_KEY=""`, so no dev data was touched and no API quota was used.

## 0. What I verified vs. assumed

| Check | Result |
|---|---|
| `pytest backend/tests` (isolated DB, no API key, Python 3.13.7) | ✅ **15 passed** in 26.8 s |
| `tsc --noEmit` (`npm run lint`) | ✅ exit 0 (but `strict` mode is **off**, so this check catches little) |
| `vite build` (output sent to scratch folder) | ✅ 370 KB JS / 106 KB gzip |
| Secrets in git history | ✅ Only `.env.example` files have ever been committed. `backend/.env` is ignored by git. |
| CI pipeline | ❌ None (`.github/` does not exist) |

**Not verified:**
- I did not exercise live Gemini behaviour or measure latency against the real API.
- I did not check Postgres or docker-compose at runtime.
- I could not confirm that the model in `backend/.env` (`LLM_MODEL_NAME="gemini-3.5-flash-lite"`, `EMBEDDING_MODEL_NAME="gemini-embedding-001"`) exists for your API key.
- The docs and defaults still say `gemini-1.5-flash`. To my knowledge Google has retired Gemini 1.5, so please check this.

**Assumption:** this is a university capstone/demo project (`SPKT_2023/year_4`), not a production SaaS yet. I rank severity for "a demo that should become deployable." If it will go to real customers soon, every security item moves up one level.

---

## 1. Scorecard

| # | Dimension | Score | Key evidence |
|---|---|:-:|---|
| 1 | Architecture & structure | **6** | Clean `core/db/models/schemas/services/api` layering matches AGENTS.md. Weak points: module-level singletons, a global engine swapped at runtime ([session.py#L71-L113](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L71-L113)), the same ticket lookup copy-pasted three times ([tickets.py#L101-L106](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/tickets.py#L101-L106), [L130-L135](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/tickets.py#L130-L135), [agent.py#L31-L36](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/agent.py#L31-L36)), and very large frontend components (`KnowledgeManagerView.tsx` 43 KB, `TicketFormView.tsx` 35 KB). |
| 2 | Code quality & readability | **5** | Good type hints, Pydantic v2 and docstrings. But there are hard-coded "magic" scores (`confidence=0.92`, `score: 0.85`) in [rag_service.py#L80](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L80) and [L252](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L252), and dead config (`RAG_CONFIDENCE_THRESHOLD`, `session_id` are never read). Draft replies are in English while the UI rule says Vietnamese ([ticket_service.py#L126-L137](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L126-L137)). |
| 3 | Correctness & bugs | **4** | Several real bugs (see §3): ticket-ID collisions, frontend inventing "offline" data even on HTTP 4xx/5xx, timeout mismatch that creates duplicate tickets, a verification gate that can be skipped, and an ignored workspace filter. |
| 4 | Performance | **5** | Fine at demo scale. Vector search loads every chunk and computes cosine in pure Python ([embedding_service.py#L176-L212](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/embedding_service.py#L176-L212)). BM25 re-tokenizes the whole corpus on every query ([fallback_service.py#L90-L93](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/fallback_service.py#L90-L93)). `wait_for(to_thread(...))` does not cancel the worker thread on timeout. Ticket creation waits on an LLM call. |
| 5 | Security & error handling | **3** | No authentication on any endpoint. CORS allows `"*"` with credentials. Prompt-injection guard is an English-only regex and is not applied to tickets or workspace persona fields. Raw `str(e)` is returned to clients. |
| 6 | Testing & reliability | **4** | Tests pass but mostly check response shape (`status in [passed, warning, failed]`). Tests write to the developer DB (`init_db()` on `./smartdesk.db`) and call the real Gemini API whenever a key is in `.env`. No unit tests for the BM25 engine, chunker or verification judge. No frontend tests. No CI. |
| 7 | Documentation & onboarding | **6** | Plenty of docs (README, API_CONTRACT, DESIGN, TEST_ACCEPTANCE, AGENTS). But they drift from the code: API_CONTRACT has no workspace/document endpoints, the README tree is outdated, docs claim pgvector (not used), and the root `.env.example` is an AI Studio template without `VITE_API_URL`. |
| 8 | Developer experience | **5** | The `.bat` scripts are friendly for Windows. Gaps: no Python linter or formatter, unpinned `>=` dependencies, no virtualenv in the scripts, `npm run clean` uses `rm -rf` (fails on Windows), four unused npm dependencies, and config that depends on the working directory. |
| 9 | Feature completeness vs. goal | **6** | RAG with citations, fallback, tickets, copilot drafts, multi-workspace and verification all exist end to end. Missing or fake: pgvector, multi-turn chat (`session_id` is ignored), "send reply" never sends anything, no agent roles, and the offline mode fabricates success. |
| 10 | Maintainability & scalability | **4** | No migrations (hand-written `ALTER TABLE` for SQLite only), a silent Postgres→SQLite fallback, in-process state (cooldown timers, BM25 index) that breaks with more than one worker, and hard-coded workspace IDs 1/2/3 in business logic ([fallback_service.py#L158-L165](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/fallback_service.py#L158-L165), [session.py#L238-L241](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L238-L241)). |

**Overall: ~4.8 / 10**

---

## 2. Summary

SmartDesk AI has a well-organised FastAPI backend and a feature-rich React frontend. The happy path works, the build is green and all 15 backend tests pass. The main weakness is reliability, not structure. Several "graceful fallback" paths hide failures instead of handling them: the frontend invents tickets, verification reports and publish confirmations whenever any request fails, including validation errors. The backend verification gate also approves documents by default. There is no authentication at all, so anyone who can reach port 8000 can read customer PII, rewrite AI personas and publish unverified knowledge. Most of the fixes are small and local, so a 1–2 week hardening pass would raise the project substantially.

## 3. Strengths (keep these)

- **Layered backend that matches the rules.** Routers are thin, logic sits in `services/`, and Pydantic schemas sit at the edges ([api.py](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/api.py)).
- **Circuit breaker idea.** The 429 cooldown ([llm_service.py#L117-L120](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/llm_service.py#L117-L120)) plus a deterministic BM25 fallback is a sound pattern, and `is_fallback` / `fallback_reason` are exposed to the UI.
- **Tenant isolation in the fallback path.** Non-default workspaces never receive the IT FAQ ([fallback_service.py#L164-L183](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/fallback_service.py#L164-L183)).
- **Ingestion guards.** 10 MB, 15-page and 40-chunk limits, rejection of scanned PDFs, and encoding fallback ([document_service.py#L18-L86](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/document_service.py#L18-L86)).
- **Central API client with status mappers.** All network calls go through [api.ts](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts), and `mapBackendStatusToFrontend` / `mapFrontendStatusToBackend` exist as AGENTS.md requires.
- **Consistent error envelope.** Errors return `{detail, error_code, status_code}` ([exceptions.py](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/core/exceptions.py)).
- **Secret hygiene.** `.env*` is gitignored and nothing sensitive is in the history.
- **Strong product docs.** DESIGN.md and TEST_ACCEPTANCE.md give a clear target to test against.

---

## 4. Problems

### Critical

| ID | Problem | Evidence | Impact |
|---|---|---|---|
| C1 | **Frontend treats every failure as "offline" and fabricates success** | Each `catch` in [api.ts](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts) handles HTTP 4xx/5xx the same as a network error, e.g. `createTicket` [L281-L328](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L281-L328), `publishDocument` [L905-L915](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L905-L915) (shows a **success** toast), `verifyDocument` [L846-L871](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L846-L871) (returns a fake `0.94 / passed` report), and `deleteDocument` [L815-L820](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L815-L820). | A 422 (bad email), 400 (prompt injection) or 500 produces a fake local ticket with a random `#TICK-xxxx`. Agents see "Resolved" or "Published" that never reached the server. Data loss with no visible error. |
| C2 | **Frontend timeout is shorter than the backend's worst case → duplicate tickets** | Frontend: chat and ticket requests time out at 4.5 s ([api.ts#L177](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L177), [L278](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L278)). Backend: `backend/.env` sets `LLM_TIMEOUT_SECONDS=5.0` (AGENTS.md says 4.0 max). Chat can spend up to 5 s on the embedding plus 5 s on the LLM; ticket creation waits up to 5 s on the draft ([ticket_service.py#L163](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L163)). | When Gemini is slow, the backend saves ticket A while the frontend aborts and shows fake ticket B. The customer gets a ticket code that does not exist. The rule "First token < 1.5 s" also cannot be met. |
| C3 | **Ticket code generator collides** | `sequence_num = 1001 + count(tickets)` ([ticket_service.py#L144-L148](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L144-L148)) while seed data uses `#TICK-1039/1041/1042`. | Derived from the code, not executed: the **36th** ticket created after seeding gets `#TICK-1039`, violates the unique constraint and returns 500. Combined with C1 the frontend then shows a fake ticket. Concurrent requests or deletions also cause collisions. |
| C4 | **No authentication or authorization anywhere** | No auth dependency on any router ([api.py](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/api.py)). `GET /tickets` returns every customer name and email ([tickets.py#L49-L86](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/tickets.py#L49-L86)). `PUT /workspaces/{id}` lets anyone rewrite `business_rules`, which is inserted directly into the LLM system prompt ([rag_service.py#L223-L225](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L223-L225)). | PII leak, unrestricted prompt injection through persona fields, anyone can delete or publish knowledge. Blocks any real deployment. |

### High

| ID | Problem | Evidence | Impact |
|---|---|---|---|
| H1 | **Verification gate approves by default and can be skipped** | Unparseable LLM output becomes `score 0.85, "passed"` ([verification_service.py#L32-L67](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/verification_service.py#L32-L67)). The deterministic judge never scores below 0.60, so it can never return `failed` ([L198-L199](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/verification_service.py#L198-L199)). `publish_document` does not check the document status ([L428-L441](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/verification_service.py#L428-L441)). Seed documents are auto-published ([session.py#L245-L262](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L245-L262)). | The headline anti-hallucination feature gives no real guarantee. A `failed` or `pending` document can go live. |
| H2 | **Workspace filter is silently dropped in the Agent Dashboard** | The dashboard sends `filters.workspace_id` ([AgentDashboardView.tsx#L98](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/components/AgentDashboardView.tsx#L98)) but `getTickets` never adds it to the URL ([api.ts#L336-L358](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L336-L358)). `App.tsx` loads all tickets with no filter ([App.tsx#L42](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/App.tsx#L42)). | Agents see other tenants' tickets, breaking the isolation the multi-tenant feature promises. |
| H3 | **Cross-tenant leak in copilot drafts** | `fallback_service.match_faq(f"{subject} {description}")` has no `workspace_id` ([ticket_service.py#L92](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L92)), so it always uses the IT FAQ. It also inserts the fallback message ("Hệ thống trợ lý AI đang bận…") as "Knowledge Base Reference". | Dental or retail drafts are grounded on IT SaaS articles, which leads to wrong replies. |
| H4 | **Silent Postgres → SQLite fallback** | Any Postgres error switches to a local SQLite file without failing ([session.py#L104-L113](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L104-L113)). Seeding errors are swallowed ([L267-L269](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L267-L269)). | In docker or production, a short DB outage at startup means data goes into a container-local file and is lost. |
| H5 | **Database location and config depend on the working directory** | `env_file=".env"` and `sqlite+aiosqlite:///./smartdesk.db` are relative paths. Two DB files already exist: `./smartdesk.db` (336 KB) and `backend/smartdesk.db` (610 KB). AGENTS.md says to run `pytest backend/tests/` from the repo root, which skips `backend/.env` entirely. | Running from the root vs `backend/` gives different data and settings. Tests pollute the developer DB. |
| H6 | **Prompt-injection guard is weak and partial** | 11 English-only regexes ([security.py#L7-L19](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/core/security.py#L7-L19)) for a Vietnamese product (e.g. "bỏ qua mọi hướng dẫn trước" passes). Not applied to ticket text or workspace fields, which reach the LLM prompts ([ticket_service.py#L95-L113](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L95-L113)). | Easy to bypass. Agents may approve drafts written by an attacker. |
| H7 | **CORS wildcard with credentials** | Default `CORS_ORIGINS` includes `"*"` ([config.py#L34-L40](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/core/config.py#L34-L40)) together with `allow_credentials=True` ([main.py#L54-L61](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/main.py#L54-L61)). | Any origin can call the API whenever `.env` does not override this. |

### Medium

| ID | Problem | Evidence |
|---|---|---|
| M1 | Duplicate citations in RAG context | `retrieve_context_documents` adds BM25 results in two consecutive blocks; when BM25 returns fewer than `top_k` hits, the same docs are added twice ([rag_service.py#L63-L98](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L63-L98)). The DB `FAQItem` query result is fetched and never used ([L66-L68](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L66-L68)). |
| M2 | Fake confidence scores | `confidence=0.92` is always returned for grounded answers; low-similarity chunks are never filtered (the comment at [L48](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/rag_service.py#L48) says `< 0.2` but no code does it); `RAG_CONFIDENCE_THRESHOLD` is unused. Escalation advice is therefore meaningless. |
| M3 | Pseudo-embeddings are random vectors | `generate_pseudo_embedding` uses a hash seed ([embedding_service.py#L54-L67](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/embedding_service.py#L54-L67)), so similarity is noise. Chunks embedded during a 429 cooldown stay random forever, and real query vectors are compared against them. |
| M4 | Verification can leave a document stuck in `processing` | Status is committed before the pipeline runs ([verification_service.py#L324-L325](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/verification_service.py#L324-L325)); any exception afterwards leaves it there. |
| M5 | Inconsistent SLA tables | Backend uses High=6 h, Medium=12 h ([ticket_service.py#L22-L27](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/services/ticket_service.py#L22-L27)). Frontend fallback uses 4 h / 8 h ([api.ts#L89-L91](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L89-L91), [L300-L307](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L300-L307)). Seeds use High=4. |
| M6 | Health and smoke test can never fail | `/health` returns 200 even when degraded; `/smoke-test` returns `"PASS (Fallback Emulated)"` on any error ([health.py#L68-L81](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/health.py#L68-L81)), so the AGENTS.md §6.1 latency benchmark cannot detect a problem. |
| M7 | Misleading "send reply" | "Đã gửi phản hồi đến …" success toast even in the `catch` branch ([AgentDashboardView.tsx#L136-L138](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/components/AgentDashboardView.tsx#L136-L138)); no email or notification mechanism exists. |
| M8 | Internal errors leak to clients | `detail=f"Lỗi hệ thống…: {str(e)}"` in [documents.py#L70](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/documents.py#L70), [L178](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/documents.py#L178), [L245](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/api/v1/endpoints/documents.py#L245); `/health` also returns the DB exception text. |
| M9 | No schema migrations | Hand-written `ALTER TABLE` for SQLite only ([session.py#L78-L95](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/backend/app/db/session.py#L78-L95)). New columns on Postgres would fail `create_all` silently. |
| M10 | Unpinned and duplicate dependencies | `requirements.txt` uses only `>=`; ships both `google-genai` and the deprecated `google-generativeai`; `pytest` is installed in the production image. npm `express`, `dotenv`, `@google/genai` and `motion` are never imported. |

### Low

| ID | Problem | Evidence |
|---|---|---|
| L1 | TypeScript not strict | [tsconfig.json](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/tsconfig.json) has no `"strict": true`; `(import.meta as any)` in [api.ts#L34](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/services/api.ts#L34). This is how H2 went unnoticed. |
| L2 | Warning toast uses a spinning loader icon | [App.tsx#L108-L110](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/src/App.tsx#L108-L110) |
| L3 | Docs drift | API_CONTRACT has no `/workspaces` or `/documents`; README tree lacks `KnowledgeManagerView`; root `.env.example` and `vite.config.ts` comments refer to AI Studio; `metadata.json` text is mis-encoded. |
| L4 | `npm run clean` uses `rm -rf` | Breaks on Windows cmd, which is the target OS. |
| L5 | Repo clutter | Two `.pytest_cache` dirs and two `smartdesk.db` files in the working tree (all gitignored). The 37 KB `implementation_plan_*.md` and `PROPOSAL.md` are committed next to the canonical docs. |

---

## 5. Risks

| Risk | Likelihood | Why it matters |
|---|---|---|
| **Demo fails live because Gemini is slow** | High | Because of C2 and C1, a slow response produces a fake ticket code or silently switches to a local mock answer. The audience sees inconsistent data between tabs. |
| **Model name or SDK retirement** | Medium–High | Docs and defaults point to `gemini-1.5-flash` / `text-embedding-004` (to my knowledge retired). The legacy `google-generativeai` SDK is deprecated. A wrong model name makes every chat request fall back without anyone noticing. |
| **Hitting the 36th-ticket collision during acceptance testing** | Medium | C3 is deterministic, and repeated test runs against the dev DB move closer to it. |
| **Scaling past one worker** | Medium (if deployed) | Cooldown timers, the BM25 index and `localFallback*` are per-process; `uvicorn --workers N` would behave inconsistently. |
| **Grader or reviewer probes security** | Medium | Unauthenticated `GET /api/v1/tickets` exposes every customer email; a simple Vietnamese jailbreak bypasses the guardrail. |
| **Postgres in docker-compose silently becomes SQLite** | Low–Medium | H4: data disappears when the container restarts. |

---

## 6. Upgrade proposals

### 6.1 Quick wins (< 1 day each)

| # | Change & why | Benefit | Effort | Risk | Steps |
|---|---|---|:-:|:-:|---|
| Q1 | **Only fall back on real network failures (C1)** | Stops fabricated tickets and fake publish/verify results | S | Low | 1) In `fetchWithTimeout` callers, throw an `ApiError(status, body)` for `!res.ok`. 2) Use local fallback only for `TypeError` / `AbortError`. 3) For 4xx, show the server `detail` as an error toast. 4) Remove fake success from `publishDocument`, `verifyDocument`, `deleteDocument`, `updateTicketStatus`. |
| Q2 | **Align timeout budgets (C2)** | Backend fallback has time to answer; no duplicate tickets | S | Low | 1) Set `LLM_TIMEOUT_SECONDS=4.0` in `backend/.env`. 2) Give the embedding call its own ~1.5 s timeout. 3) Wrap `answer_query` in one overall `asyncio.wait_for` of about 4.5 s. 4) Set frontend chat timeout to about 7 s and ticket creation to about 10 s (or see S3). |
| Q3 | **Fix ticket code generation (C3)** | No 500s, no collisions | S | Low | Derive the code from the DB primary key after `flush()`: `f"#TICK-{1000 + ticket.id}"`, or `max(ticket_code)+1` inside the transaction. Add a test that creates 50 tickets. |
| Q4 | **Make verification fail closed and enforce the publish gate (H1, M4)** | The anti-hallucination claim becomes true | S | Low | 1) Parse failure → `score 0.0, "failed"`. 2) Deterministic judge range 0–1 so `failed` is possible. 3) `publish_document` raises unless status is `verified`. 4) `try/finally` resets `processing` → `failed`. |
| Q5 | **Pass `workspace_id` through (H2, H3)** | Real tenant isolation | S | Low | Add `workspace_id` to the `getTickets` filter type and the URL params; pass `currentWorkspaceId` from `App.tsx`; call `match_faq(..., workspace_id=ws_id)` in `generate_draft_reply`. |
| Q6 | **Make paths independent of the working directory (H5)** | One DB, one config, whatever directory you start from | S | Low | Resolve `env_file` and the default SQLite path relative to `Path(__file__).parents[2]`; delete the stray root `smartdesk.db`. |
| Q7 | **Lock CORS and hide internal errors (H7, M8)** | Basic hardening | S | Low | Remove `"*"` from defaults; refuse `"*"` when credentials are allowed. Log `str(e)` server-side and return a generic Vietnamese message. |
| Q8 | **Fix the duplicate-citation bug and dead code (M1, M2 part)** | Cleaner prompts and citations | S | Low | Merge the two BM25 blocks, dedupe by `doc_id`, drop the unused `FAQItem` query, apply a minimum similarity score. |
| Q9 | **Clean dependencies and config (M10, L1, L4)** | Smaller, reproducible builds | S | Low | Remove unused npm deps; pin Python versions (`pip freeze` → `requirements.txt`, move pytest to `requirements-dev.txt`); drop `google-generativeai`; replace `rm -rf` with `rimraf`. |

### 6.2 Short-term (1–2 weeks)

| # | Change & why | Benefit | Effort | Risk | Steps |
|---|---|---|:-:|:-:|---|
| S1 | **Minimal auth for agent/admin endpoints (C4)** | Removes the PII exposure; allows a real deployment | M | Medium | Keep it simple: 1) `AGENT_API_KEY` in `.env`, checked by a `Depends(require_agent)` on `/tickets` GET/PATCH, `/agent`, `/workspaces` POST/PUT, `/documents/*`. 2) Keep `/chat` and `POST /tickets` public, with rate limiting (`slowapi`). 3) Frontend agent tab sends the header. Move to JWT and roles later (L1). |
| S2 | **Isolated test setup + CI (testing score)** | Trustworthy green builds | M | Low | 1) `conftest.py` that sets `DATABASE_URL` to a temp file and `GEMINI_API_KEY=""` **before** importing `app`. 2) Function-scoped DB or transaction rollback. 3) Add unit tests for `BM25Engine`, `recursive_character_splitter`, `clean_json_response`, ticket code and timeout fallback (mock `llm_service`). 4) GitHub Actions: `ruff`, `pytest`, `npm ci && npm run lint && npm run build`. |
| S3 | **Generate the copilot draft after ticket creation** | Ticket creation answers in < 200 ms; removes the C2 class of bugs | M | Low | Save the ticket with `ai_draft_reply=None`, then use FastAPI `BackgroundTasks` to generate the draft. The dashboard shows a "Đang soạn bản nháp…" state and has the existing "regenerate" button. |
| S4 | **Broaden the injection guard and apply it consistently (H6)** | Covers Vietnamese attacks; protects agents | M | Low | Add Vietnamese patterns plus diacritic-insensitive matching; run the check on ticket subject/description and workspace fields; wrap untrusted text in clear delimiters (`<customer_input>…</customer_input>`) in every prompt; add tests. |
| S5 | **Fail fast on DB errors; add Alembic (H4, M9)** | Safe Postgres deployments | M | Medium | Remove the silent fallback, or allow it only when `ENV=dev`. `alembic init`, autogenerate a baseline from the current models, and remove `_migrate_sqlite_columns`. Move seeding to a separate `python -m app.seed` command. |
| S6 | **Honest health checks and confidence (M2, M6)** | Monitoring and escalation actually mean something | S–M | Low | `/health` returns 503 when degraded; smoke test reports `FAIL`/`FALLBACK`. Confidence comes from the top retrieval score; `escalation_recommended = score < RAG_CONFIDENCE_THRESHOLD`. |
| S7 | **Refresh docs to match the code (L3)** | Faster onboarding, fewer AI-assistant errors | S | Low | Add workspace/document endpoints to API_CONTRACT; update the README tree; replace the root `.env.example` with `VITE_API_URL=…`; record the actual Gemini model names; mark pgvector as "planned". |
| S8 | **Split the largest components** | Easier review and safer changes | M | Low | Pull `KnowledgeManagerView` into `WorkspaceSettingsPanel`, `DocumentList`, `VerificationReportModal`; move ticket-lookup logic into a backend `get_ticket_or_404()` helper. Turn on `"strict": true` gradually. |

### 6.3 Long-term (strategic)

| # | Change & why | Benefit | Effort | Risk | Steps |
|---|---|---|:-:|:-:|---|
| L1 | **Proper multi-tenant auth** (users, roles: customer / agent / admin, workspace membership) | Real SaaS readiness | L | Medium | JWT (`fastapi-users` or hand-rolled), a `workspace_members` table, and a query filter enforced in one dependency. |
| L2 | **Use pgvector for real** | Search scales beyond a few thousand chunks; matches the docs | M–L | Medium | `Vector(768)` column on Postgres; keep the Python cosine path for SQLite dev; HNSW index; mark chunks embedded with pseudo-vectors as `needs_reembed` and re-embed them with a job. |
| L3 | **Background job queue for ingestion and verification** | No 15 s HTTP requests; retries | M | Medium | Start with FastAPI `BackgroundTasks` + status polling; move to `arq` / RQ with Redis only if needed. Shared state (cooldown) also goes into Redis to allow several workers. |
| L4 | **Redesign the offline mode** | Either a clear read-only demo mode or an outbox, never silent fakes | M | Low | Show an explicit "Chế độ demo ngoại tuyến" banner; block writes, or queue them in `localStorage` and replay with idempotency keys once the backend is back. |
| L5 | **Multi-turn chat and a RAG quality loop** | Uses `session_id`; measures hallucination over time | L | Medium | Store conversation turns; keep a small golden Q&A set per workspace run in CI (the verification engine can be reused); track answer and fallback rates. |
| L6 | **Real reply delivery** | Closes the agent workflow | M | Low | SMTP or transactional email provider; `ticket_messages` table; "send" only after explicit agent approval (already a rule). |

---

## 7. Top-5 priorities (impact ÷ effort)

| Rank | Item | Fixes | Effort | Why first |
|:-:|---|---|:-:|---|
| **1** | **Q1 — Stop fabricating success on HTTP errors** | C1, M7 | S | Biggest source of silent data loss and confusing demos; changes are limited to `api.ts`. |
| **2** | **Q3 + Q2 — Fix ticket ID generation and align timeouts** | C3, C2 | S | Two deterministic bugs that will hit a live demo; together under half a day. |
| **3** | **Q4 — Fail-closed verification and an enforced publish gate** | H1, M4 | S | Turns the flagship anti-hallucination claim from cosmetic into real. |
| **4** | **Q5 + Q6 — Real tenant isolation and fixed paths** | H2, H3, H5 | S | Small edits that make multi-workspace behaviour correct and tests reproducible. |
| **5** | **S2 — Isolated test setup + CI** | Testing, DX | M | Locks in fixes 1–4 so later regressions get caught automatically. |

*Next after these:* S1 (minimal API-key auth) is the most important item for anything beyond a classroom demo.
