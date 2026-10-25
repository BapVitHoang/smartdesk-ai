# AI Usage, Verification & Engineering Log (`AI_USAGE.md`)

> **Project:** SmartDesk AI – Intelligent Customer Support & Knowledge Synthesizer  
> **Requirement Alignment:** `REQ-28` / `CRIT-06` & `CRIT-09` (Mandatory AI Usage Disclosure, 4-Gate Verification Protocol, and Real Failure/Fix Case Studies)  
> **Single Source of Truth for Team Members:** [`docs/TEAM_ROSTER.md`](./docs/TEAM_ROSTER.md)  
> **Team Members & Workstreams:**
> - **Dev A (AI Engine, RAG Pipeline & Evaluation):** Lê Nguyên (`@TheOrijinnn`, MSSV `23110043`)
> - **Dev B (Platform, Data & Security) & Integrator:** Ngô Việt Hoàng (`@BapVitHoang`, MSSV `23110020`)
> - **Dev C (Frontend UX, QA & Documentation):** Tống Gia Khánh (`@TKhanh`, MSSV `23110032`)

---

## 1. AI Tools & Models Used During Development

| Workstream / Member | AI Tool / Model | Primary Use Cases | Governance & Verification Scope |
| :--- | :--- | :--- | :--- |
| **Dev A (Lê Nguyên / `@TheOrijinnn`)** | Google Antigravity Coding Assistant (Gemini 3.5 / Claude) | RAG pipeline, tool registration (`agent_tools.py`), structured outputs (`ai_structured.py`), 24-case benchmark evaluation (`run_eval.py`). | Verified against `CONTRACTS.md`, live Gemini API parameter specs, and unit tests (`backend/tests/ai/`). |
| **Dev B & Integrator (Ngô Việt Hoàng / `@BapVitHoang`)** | Google Antigravity Coding Assistant (Claude 3.7 / Gemini 3.5) | FastAPI architecture, pgvector dual-dialect mapping, salted scrypt password hashing, sliding-window throttle, JWT secret hardening, Docker Compose orchestration. | Verified with clean venv AST audit, offline security suites (`test_auth_security.py`, `test_jwt_secret.py`), Docker Compose smoke test (`smoke_docker.ps1`). |
| **Dev C (Tống Gia Khánh / `@TKhanh`)** | Google Antigravity Coding Assistant (Gemini 3.5 / Claude) | React 19 SPA, SSE streaming receiver (`chat.ts`), Telemetry & Cost-Guard panel (`TelemetryPanel.tsx`), 3-agent verification trace modal, Capstone documentation (`REPORT.md`, `PRESENTATION_AND_DEMO.md`). | Verified with `npm run lint` (`tsc --noEmit`), `npm run build` (Vite 6), headless responsive verification (`1440x900`, `375x812`), and cross-feature offline flows (`test_cross_feature_flows.py`). |
| **Runtime Cloud LLM** | Google Gemini (`gemini-3.5-flash-lite`, fallback `gemini-2.5-flash-lite`) | Real-time grounded RAG chat, single-call ticket copilot triage, 3-stage synthetic QA verification. | Enforced minimal thinking budget (`thinking_level="MINIMAL"`), strict timeout (4.0s), and externalized system prompts (`prompts.json`). |
| **Runtime Cloud Embeddings** | Google `gemini-embedding-001` | Semantic embeddings for `KnowledgeChunk` and `FAQItem` records. | Verified dual-mode with PII masking (`redact_pii`). |
| **Runtime Local LLM (Dual-Mode)** | Ollama (`qwen2.5:3b` + `nomic-embed-text`) | Offline development and rate-limit-free CI execution. | Selected via `AI_PROVIDER=ollama`. |
| **Deterministic Fallback Engine** | Pure-Python Okapi BM25 + SHA-256 Pseudo-Embeddings | Non-AI deterministic fallback when offline, timeout, or rate-limited. | Fallback on `seed_faq.json` and published workspace chunks. |

---

## 2. Human Verification Workflow (How AI-Generated Code Was Audited)

Every piece of AI-assisted code or configuration was subjected to a strict 4-gate verification protocol before acceptance:
1. **Contract & Type Gate:** Checked against frozen Pydantic v2 schemas (`backend/app/schemas/`), frozen interfaces (`docs/spec/CONTRACTS.md`, `docs/API_CONTRACT.md`), and TypeScript types (`frontend/src/types.ts` via `npm run lint --prefix frontend`).
2. **Live API & Parameter Probe Gate:** Never trusted training-cutoff assumptions from AI models; verified live API behaviors with live diagnostic probes (e.g. diagnosing Gemini 3.5 `thinking_budget` vs `thinking_level="MINIMAL"`).
3. **Automated Integration Test Gate:** Executed offline pytest suites (`pytest backend/tests/ -q`) with empty `GEMINI_API_KEY` to guarantee 100% deterministic test pass without external network dependencies.
4. **Security & Governance Gate:** Verified anti-fabrication rules (`python scripts/check_roster.py`), module ownership boundaries (`python scripts/check_ownership.py`), PII redaction (`redact_pii`), and prompt injection defenses (English & Vietnamese).

---

## 3. Real AI Failure Cases & Human Fixes (Audited from Git History)

Below are 5 real failure cases where AI-generated code introduced bugs or security vulnerabilities, accompanied by diagnosis and exact commit hashes from Git history:

### Case Study 1: Gemini 3.5 Flash Lite HTTP 400 `INVALID_ARGUMENT` Parameter Incompatibility
- **Workstream:** Dev A (AI Engine)
- **Observed Issue:** Live API calls to `gemini-3.5-flash-lite` returned `HTTP 400 INVALID_ARGUMENT` on `generateContent`.
- **Root Cause:** The AI assistant configured `ThinkingConfig(thinking_budget=0)` based on documentation for other models. In `google-genai 2.24.0`, Gemini 3.5 rejects integer `thinking_budget` with `400 INVALID_ARGUMENT`.
- **Diagnosis & Fix Applied:** Bisected SDK parameters live against Google GenAI API; replaced `thinking_budget` with `types.ThinkingConfig(thinking_level="MINIMAL")`, restoring sub-1,500ms response latency.
- **Commit Hash:** Fixed by Dev A (`@TheOrijinnn` / Integrator) in commit [`cb404fe`](https://github.com/BapVitHoang/smartdesk-ai/commit/cb404fe) (*"fix(ai-engine): resolve Gemini 3.5 400 INVALID_ARGUMENT, add circuit breaker error classification, and verify audit gaps"*).

### Case Study 2: Auth Module Password Check Bypass & Google Token Forgery Vulnerability
- **Workstream:** Dev B (Platform & Security)
- **Observed Issue:** Initial AI-generated authentication accepted arbitrary passwords for any seeded account and decoded Google ID tokens without cryptographic signature verification (`verify_signature=False`).
- **Root Cause:** The assistant prioritized making local mock tests pass without external Google network dependencies or salted hashing setup.
- **Diagnosis & Fix Applied:** Implemented salted scrypt password hashing with constant-time verification (`hmac.compare_digest`), dummy hash evaluation for unknown users to prevent timing attacks, and verified Google ID token cryptographic signatures using `google.oauth2.id_token.verify_oauth2_token`.
- **Commit Hash:** Fixed by Dev B (`@BapVitHoang`) in commit [`c780921`](https://github.com/BapVitHoang/smartdesk-ai/commit/c780921) (*"fix(auth): verify passwords and Google ID token signature"*).

### Case Study 3: Known Public Default JWT Secret in Codebase
- **Workstream:** Dev B & Integrator
- **Observed Issue:** A static literal JWT secret key was hardcoded in settings and compose configuration.
- **Root Cause:** The AI assistant scaffolded a default placeholder secret for local convenience, creating a critical vulnerability where any attacker could mint valid admin tokens.
- **Diagnosis & Fix Applied:** Purged the default literal from source code; stored only its SHA-256 hash (`KNOWN_DEFAULT_JWT_SECRET_SHA256`) to detect placeholders; generated ephemeral per-process secrets (`secrets.token_urlsafe(48)`) when `DEMO_LOGIN_ENABLED=True`, and refused server startup with `RuntimeError` when demo login is disabled.
- **Commit Hash:** Fixed by Integrator (`@BapVitHoang`) in commit [`c221813`](https://github.com/BapVitHoang/smartdesk-ai/commit/c221813) (*"fix(auth): never use a known default JWT secret"*).

### Case Study 4: Hallucinated Lucide Icon Member & TypeScript Compilation Crash
- **Workstream:** Dev C (Frontend UX)
- **Observed Issue:** `npm run build` crashed with `error TS2724: '"lucide-react"' has no exported member named 'MessageSquareCheck'`.
- **Root Cause:** The AI assistant hallucinated an icon component name that does not exist in `lucide-react`.
- **Diagnosis & Fix Applied:** Replaced the non-existent icon with canonical `MessageSquare` and validated strict TypeScript type checking (`tsc --noEmit`).
- **Commit Hash:** Fixed by Dev C (`@TKhanh`) in commit [`1b78353`](https://github.com/BapVitHoang/smartdesk-ai/commit/1b78353) (*"feat(ux): implement rbac role switcher, ticket sorting, pagination, delete, and multi-agent trace"*).

### Case Study 5: Unbounded Query Count Clashing with RBAC Tenant Filters
- **Workstream:** Dev B (Tickets & Data)
- **Observed Issue:** The pagination count query `select(func.count(Ticket.id))` returned the total ticket count of the whole database in `X-Total-Count` instead of the user's filtered count.
- **Root Cause:** The AI assistant built the count query separately without replicating active RBAC user email and tenant where-clauses.
- **Diagnosis & Fix Applied:** Replicated all active where clauses (RBAC customer email filter, workspace ID, status, category, priority, search) into `count_query`.
- **Commit Hash:** Fixed by Dev B (`@BapVitHoang`) in commit [`deee867`](https://github.com/BapVitHoang/smartdesk-ai/commit/deee867) (*"feat(tickets): add server-side sorting, X-Total-Count header, delete API and copilot triage"*).

---

## 4. Benchmark & Evaluation Summary

Across all 24 evaluation test cases in `backend/data/eval_dataset.json` evaluated in `backend/scripts/run_eval.py`:
- **Legacy Baseline Pass Rate:** 8/24 (`33.3%`)
- **Upgraded Pipeline Pass Rate:** 24/24 (`100.0%`)
- **Delta Improvement:** `+66.7%` (`+16` cases improved)
- **Breakdown:** 10/10 Normal (`100%`), 6/6 Edge (`100%`), 8/8 Should-Refuse (`100%`).
