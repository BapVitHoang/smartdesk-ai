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

### 1.1 Prompt chính theo từng phần (Key Prompts)

Nguyên văn được trích từ nhật ký của từng thành viên (`docs/notes/*-ai-usage.md`). Cột "Đã kiểm tra / sửa" tóm tắt bước xác minh đã ghi trong cùng nhật ký.

| Phần | Thành viên | Công cụ | Prompt chính (nguyên văn) | Đã kiểm tra / sửa | Nguồn |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Structured output & Ticket Copilot | Dev A | Google Antigravity (Gemini 3.5 / Claude) | "Implement `generate_structured_output()` in `llm_service.py` and `generate_ticket_triage_and_draft()` in `ticket_copilot_service.py` adhering to `CONTRACTS.md` §4 & §7, normalizing `'Technical Bug'` to `'Bug Report'` and providing a deterministic Vietnamese fallback when Gemini is in cooldown." | Đối chiếu `CONTRACTS.md`, test `backend/tests/ai/` | [A-ai-usage.md](docs/notes/A-ai-usage.md#L11) |
| Agent tools + xác nhận 2 bước | Dev A | Google Antigravity | "Implement 4 DB-backed support tools in `backend/app/services/agent_tools.py` (`lookup_customer_tickets`, `search_workspace_knowledge`, `create_escalation_ticket`, `update_ticket_priority_or_status`) and wire two-phase confirmation in `chat_actions.py`." | Test xác nhận/hủy/hết hạn hành động | [A-ai-usage.md](docs/notes/A-ai-usage.md#L24) |
| Bộ eval 24 case | Dev A | Google Antigravity | "Create `backend/data/eval_dataset.json` (24 cases: 10 normal, 6 edge, 8 should-refuse across Workspaces 1–3) and `backend/scripts/run_eval.py` comparing Legacy Baseline vs Upgraded Pipeline." | Chạy `run_eval.py`, báo cáo `A-eval-report.md` | [A-ai-usage.md](docs/notes/A-ai-usage.md#L37) |
| Sửa lỗi Gemini 400 & circuit breaker | Dev A | Google Antigravity | "Investigate live generateContent 400 INVALID_ARGUMENT on gemini-3.5-flash-lite, bisect SDK parameters, classify errors (…), and run live evaluation." | Case Study 1 bên dưới | [A-ai-usage.md](docs/notes/A-ai-usage.md#L52) |
| OAuth2 + JWT + RBAC | Dev B | Google Antigravity (Claude 3.7 / Gemini 3.5) | "Hoàn thiện Task B1: Xác thực OAuth2 + HS256 JWT, Phân quyền RBAC (admin/user) & Cô lập dữ liệu trong auth.py, deps.py, tickets.py và agent.py." | Test `test_auth_module.py`, `tests/platform/` | [B-ai-usage.md](docs/notes/B-ai-usage.md#L12) |
| CRUD, sort, phân trang ticket | Dev B | Google Antigravity | "Bổ sung DELETE, Server-Side Sorting, Pagination Header X-Total-Count & Kết nối Copilot trong ticket_service.py, tickets.py, workspaces.py." | Case Study 5 bên dưới | [B-ai-usage.md](docs/notes/B-ai-usage.md#L26) |
| pgvector dual-dialect | Dev B | Google Antigravity | "Kích hoạt Dual-Dialect pgvector trên PostgreSQL trong knowledge.py, session.py, embedding_service.py và hoàn thiện test platform." | `test_pgvector_and_db.py` | [B-ai-usage.md](docs/notes/B-ai-usage.md#L40) |
| Vá bảo mật xác thực | Dev B | Google Antigravity | "Khắc phục triệt để lỗ hổng xác thực: kiểm tra mật khẩu bằng salted scrypt, xác thực chữ ký Google ID token qua google-auth, chặn đăng nhập tài khoản ảo và bổ sung sliding-window throttle chống brute-force." | Case Study 2 bên dưới | [B-ai-usage.md](docs/notes/B-ai-usage.md#L51) |
| JWT secret, Docker smoke | Dev B & Integrator | Google Antigravity | "Thực hiện các tác vụ platform cho Dev B và Integrator: Không bao giờ dùng default JWT secret trong code; …; Thêm scripts/smoke_docker.ps1 cho Docker/pgvector; …" | Case Study 3 bên dưới | [B-ai-usage.md](docs/notes/B-ai-usage.md#L69) |
| SSE streaming UI & thẻ xác nhận | Dev C | Google Antigravity (Gemini 3.5 / Claude) | "Implement SSE token streaming in ChatView.tsx with pulsing cursor, violet tool call badges, and an interactive Vietnamese Two-Phase Confirmation Card for pending mutating actions calling POST /api/v1/chat/confirm-action." | `npm run lint`, `npm run build` | [C-ai-usage.md](docs/notes/C-ai-usage.md#L12) |
| Telemetry panel | Dev C | Google Antigravity | "Connect TelemetryPanel.tsx to GET /api/v1/agent/ai-usage and POST /api/v1/agent/ai-usage/reset-cooldown. Embed the panel inside AgentDashboardView with a view switcher tab." | Sửa lỗi TS2353 (ghi trong nhật ký) | [C-ai-usage.md](docs/notes/C-ai-usage.md#L27) |
| RBAC switcher, sort, phân trang, trace UI | Dev C | Google Antigravity | "Implement 1-click RBAC switcher between Admin and User in Header, hide/lock admin tabs when role=user, add sort/pagination/delete in AgentDashboard, and embed 3-agent verification trace in KnowledgeManagerView modal." | Case Study 4 bên dưới | [C-ai-usage.md](docs/notes/C-ai-usage.md#L41) |
| Báo cáo, slide, README | Dev C | Google Antigravity | "Generate formal 7-chapter project report in docs/REPORT.md, 15-slide outline with 8-min demo script and 10-min live change playbook in docs/PRESENTATION_AND_DEMO.md, and update README.md and docs/PROPOSAL.md with test accounts and team roster." | Rà soát cả nhóm | [C-ai-usage.md](docs/notes/C-ai-usage.md#L58) |
| Test luồng liên tính năng | Dev C | Google Antigravity | "Write offline cross-feature integration tests in backend/tests/common/ covering the full customer journey: login -> list tickets -> submit ticket form -> chat assistant -> tool call escalation -> two-phase action confirmation, using existing conftest fixtures." | `pytest backend/tests/common` | [C-ai-usage.md](docs/notes/C-ai-usage.md#L70) |
| Khắc phục danh sách thiếu sót sau tự đánh giá (LLM function calling, streaming thật, JWT cho tài liệu/workspace, trace lưu DB, prompt ra `prompts.json`, chi phí TB/request, sửa câu chữ UI) | CHƯA CÓ DỮ LIỆU (thành viên thực hiện tự điền) | GitHub Copilot (VS Code agent) | "hoàn thành các việc trong ## 4. Danh sách còn thiếu theo ưu tiên (C)" (dựa trên `DANH_GIA_HE_THONG.md`) | Chạy `pytest backend/tests` ở chế độ offline (`GEMINI_API_KEY=" "`): 167 passed, 2 skipped; `npm run lint`, `npm run build` đạt; test mới `tests/ai/test_llm_tool_calling_and_streaming.py`, `tests/platform/test_document_workspace_auth.py`. Chưa kiểm chứng function calling/streaming với Gemini thật (khóa trong máy trả HTTP 403 PERMISSION_DENIED) | Phiên làm việc ngày 2026-10-26 |

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
