# SmartDesk AI — Workstream Specification & Task Allocation

> **Version:** 1.1.0  
> **Status:** FROZEN GOVERNANCE SPECIFICATION  
> **Target Branch:** `Hoang`  
> **Governing Documents:** [`AGENTS.md`](../../AGENTS.md), [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md), [`docs/spec/CONTRACTS.md`](../spec/CONTRACTS.md), [`docs/plan/PLAN.md`](./PLAN.md)

---

## 1. Overview & Workstream Philosophy

### 1.1 The "Stay in Your Lane" Principle
To achieve high velocity without merge conflicts among a **team of exactly 3 members**, SmartDesk AI enforces a strict **Single File Ownership** architecture.

- **Zero Overlaps:** Every file tracked in Git has exactly **one owner**. No two developers ever edit the same file in their feature branches.
- **Team Structure (3 Members):**
  - **Dev A (Owner 1):** AI Engine & Evaluation (`@TheOrijinnn`)
  - **Dev B (Owner 2) & Integrator:** Platform, Data & Security + Integrator Hat (`@BapVitHoang`)
  - **Dev C (Owner 3):** Frontend UX, QA & Capstone Documentation (`@TKhanh`)
  - *Note: Hoang is Dev B and simultaneously wears the Integrator hat. There is no separate fourth person.*
- **Frozen Contracts:** All inter-module communication is mediated exclusively through frozen signatures defined in [`docs/spec/CONTRACTS.md`](../spec/CONTRACTS.md) and [`frontend/src/types.ts`](../../frontend/src/types.ts).
- **No Blocked Dependencies:** When a service needs a capability from another workstream that is not yet merged, it relies on contract stubs and deterministic mocks (defined in `CONTRACTS.md` and `frontend/src/services/mocks/`).
- **Cross-Workstream Change Protocol:** If Developer X requires a change in a file owned by Developer Y or the Integrator, Developer X creates a formal request file in `docs/requests/dev<A|B|C>.md`. Developer X **never** modifies the foreign file directly.
- **Automated Verification:** The pre-commit gate `python scripts/check_ownership.py --owner <dev>` programmatically blocks any commit violating ownership boundaries.

### 1.2 Workload Balance Analysis
Each workstream is balanced in scope and technical depth:
- **Dev A (AI Engine & QA):** $\sim 6.5\text{ hours}$ (Structured output, agent tools, prompt management, evaluation benchmark).
- **Dev B (Platform, Data & Security + Integrator Hat):** $\sim 6.0\text{ hours}$ platform features + release integration duties (Auth/JWT/RBAC, ticket CRUD/sorting/pagination, `pgvector`, container configuration, CI/contracts).
- **Dev C (Frontend UX, Integration QA & Docs):** $\sim 6.5\text{ hours}$ (UI integration, cross-feature tests, user stories, report, defense slides).

---

## 2. Workstream Breakdowns

### 2.1 Developer A — AI Engine & Quality Assurance
- **Mission:** Build and harden the core AI pipeline, including single-call Pydantic structured output, tool-calling agent with user confirmation, prompt externalization, and the 24-case AI evaluation benchmark.
- **Assigned Tasks:**
  - `TASK-08`: Capability C (Pydantic Structured Output) & Capability E (Multi-Agent Verification Trace)
  - `TASK-09`: Capability B (Tool-Using Agent with 4 DB Tools & Confirmation Schema)
  - `TASK-11 (backend)`: SSE Token Streaming endpoint (`POST /api/v1/chat/stream`) & generator methods
  - `TASK-15`: 24-case AI Evaluation Benchmark (`eval_dataset.json` & `run_eval.py`)
- **Exclusive Owned Paths:**
  ```text
  backend/app/services/llm_service.py
  backend/app/services/rag_service.py
  backend/app/services/ticket_copilot_service.py
  backend/app/services/verification_service.py
  backend/app/services/agent_tools.py
  backend/app/schemas/ai_structured.py
  backend/app/schemas/chat.py
  backend/app/schemas/verification.py
  backend/app/api/v1/endpoints/chat.py
  backend/app/api/v1/endpoints/chat_stream.py
  backend/app/api/v1/endpoints/chat_actions.py
  backend/app/api/v1/endpoints/ai_usage.py
  backend/app/api/v1/endpoints/knowledge.py
  backend/app/core/prompts.py
  backend/data/prompts.json
  backend/data/seed_faq.json
  backend/data/finetune_alpaca.jsonl
  backend/data/sample_documents/*
  backend/data/eval_dataset.json
  backend/scripts/run_eval.py
  backend/scripts/export_finetune_dataset.py
  Modelfile
  backend/tests/ai/**
  backend/tests/test_rag_module.py
  backend/tests/test_ollama_provider.py
  docs/notes/A.md
  docs/notes/A-ai-usage.md
  docs/notes/A-eval-report.md
  docs/requests/devA.md
  ```
- **Contracts Used:**
  - Reads `User` and `current_user` via `backend/app/core/deps.py` (`get_current_user`).
  - Calls `log_ai_call()` from `backend/app/services/ai_usage_logger.py`.
  - Reads DB chunks via `backend/app/models/knowledge.py`.
- **Mocks to Use:**
  - Use `conftest.py` dependency override fixtures (`client`, `admin_client`, `user_client`, `unauth_client`).
  - Use deterministic fallback mock in `llm_service.py` (`cooldown_until`) when testing without Google API keys.
- **Definition of Done (DoD):**
  1. `pytest backend/tests/test_rag_module.py backend/tests/test_ollama_provider.py backend/tests/ai/ -v` passes with 0 failures.
  2. `run_eval.py` reports REAL results; baseline vs upgraded numbers come from actually running both pipelines; the report states what deterministic mode measures (retrieval, guardrails, schema) and what live mode measures (LLM answers), saved to `docs/notes/A-eval-report.md`.
  3. `python scripts/check_ownership.py --owner devA` exits 0 with 0 boundary violations.
  4. Notes documented in `docs/notes/A.md` and AI prompts logged in `docs/notes/A-ai-usage.md`.
- **Demo Script (3–5 min):**
  1. Trigger `POST /api/v1/chat/stream` with streaming query; show SSE event stream yielding metadata and token events.
  2. Ask chat to look up tickets (`lookup_customer_tickets` tool); observe live execution.
  3. Ask chat to create an escalation ticket; verify `pending_action` confirmation card schema is returned.
  4. Run `python backend/scripts/run_eval.py --mode deterministic` live; show the real measured baseline vs upgraded accuracy report.

---

### 2.2 Developer B — Platform, Data & Security (with Integrator Hat)
- **Mission:** Implement OAuth2/JWT authentication, RBAC (`admin`/`user`), user-level data isolation, full ticket CRUD with sorting/pagination/deletion, PostgreSQL `pgvector` dual-dialect support, and multi-container orchestration.
- **Assigned Tasks:**
  - `TASK-10 (backend)`: AI Usage logging schema (`AIUsageLog` model & session seeding)
  - `TASK-12 (backend)`: OAuth2 + JWT authentication, RBAC dependencies, user isolation
  - `TASK-13 (backend)`: Ticket & Workspace `DELETE`, server-side sorting (`sort_by`, `sort_order`), pagination headers
  - `TASK-14`: Dual-dialect `pgvector` (PostgreSQL + SQLite) & Docker Compose configuration
  - Integrator duties: Shared contract enforcement, CI verification, and release coordination.
- **Exclusive Owned Paths:**
  ```text
  backend/Dockerfile
  backend/app/core/deps.py
  backend/app/core/security.py
  backend/app/db/**
  backend/app/models/**
  backend/app/schemas/ticket.py
  backend/app/schemas/workspace.py
  backend/app/schemas/document.py
  backend/app/schemas/health.py
  backend/app/schemas/knowledge.py
  backend/app/schemas/auth.py
  backend/app/services/ticket_service.py
  backend/app/services/document_service.py
  backend/app/services/embedding_service.py
  backend/app/services/fallback_service.py
  backend/app/services/ai_usage_logger.py
  backend/app/api/v1/endpoints/auth.py
  backend/app/api/v1/endpoints/tickets.py
  backend/app/api/v1/endpoints/agent.py
  backend/app/api/v1/endpoints/workspaces.py
  backend/app/api/v1/endpoints/documents.py
  backend/app/api/v1/endpoints/health.py
  backend/scripts/reembed_chunks.py
  backend/tests/test_tickets_module.py
  backend/tests/test_auth_module.py
  backend/tests/test_workspace_and_verification.py
  backend/tests/platform/**
  docker-compose.yml
  docs/notes/B.md
  docs/notes/B-ai-usage.md
  docs/requests/devB.md
  ```
- **Contracts Used:**
  - Exposes `get_current_user` and `require_role` via `backend/app/core/deps.py` for Dev A.
  - Exposes `log_ai_call` via `backend/app/services/ai_usage_logger.py` for Dev A.
  - Calls `ticket_copilot_service.py` (Dev A) to generate copilot drafts during ticket triage.
- **Mocks to Use:**
  - When Dev A's copilot is not yet merged, `ticket_service.py` falls back to deterministic Vietnamese draft templates.
- **Definition of Done (DoD):**
  1. `pytest backend/tests/test_tickets_module.py backend/tests/test_auth_module.py backend/tests/test_workspace_and_verification.py backend/tests/platform/ -v` passes with 0 failures.
  2. Unauthenticated calls to secured routes return HTTP 401; non-admin calls to agent routes return HTTP 403.
  3. `docker compose config` validates cleanly without syntax errors.
  4. `python scripts/check_ownership.py --owner devB` exits 0 with 0 boundary violations.
  5. Notes documented in `docs/notes/B.md` and AI prompts logged in `docs/notes/B-ai-usage.md`.
- **Demo Script (3–5 min):**
  1. Execute `POST /api/v1/auth/token` with seeded demo credentials; receive JWT access token.
  2. Call `GET /api/v1/tickets` as `an.nguyen@company.vn`; demonstrate that only their own ticket (`#TICK-1042`) is visible.
  3. Call `GET /api/v1/tickets?sort_by=priority&sort_order=desc` as `admin@smartdesk.ai`; demonstrate multi-ticket triage and pagination headers.
  4. Perform `DELETE /api/v1/tickets/{id}`; verify HTTP 204 response and deletion from DB.
  5. Run `docker compose up --build -d` and show healthy container status.

---

### 2.3 Developer C — Frontend UX, Integration QA & Documentation
- **Mission:** Wire modern UI features (SSE token streaming bubble, tool confirmation card, telemetry dashboard, OAuth2 role switcher, pagination/sorting), maintain end-to-end integration tests, and author capstone deliverables.
- **Assigned Tasks:**
  - UI for `TASK-08..13`:
    * Streaming token bubble with pulsing cursor (`ChatView.tsx`)
    * Interactive tool confirmation card (`ChatView.tsx`)
    * Admin AI Telemetry & Cost Guard panel (`AgentDashboardView.tsx` / `features/telemetry/`)
    * OAuth2 demo login & role switcher (`Header.tsx` / `features/auth/`)
    * Ticket table sorting, deletion, and pagination controls (`AgentDashboardView.tsx` / `features/agent/`)
    * Multi-agent verification trace view (`KnowledgeManagerView.tsx` / `features/knowledge/`)
  - `TASK-16`: End-to-end and cross-feature integration test suite (`backend/tests/common/`)
  - `TASK-17`: Capstone documentation pack (`README.md`, `docs/PROPOSAL.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/TEST_ACCEPTANCE.md`)
- **Exclusive Owned Paths:**
  ```text
  frontend/src/App.tsx
  frontend/src/main.tsx
  frontend/src/index.css
  frontend/src/data.ts
  frontend/src/components/**
  frontend/src/features/**
  frontend/src/services/api/auth.ts
  frontend/src/services/api/chat.ts
  frontend/src/services/api/documents.ts
  frontend/src/services/api/telemetry.ts
  frontend/src/services/api/tickets.ts
  frontend/src/services/api/workspaces.ts
  frontend/src/services/mocks/**
  frontend/metadata.json
  backend/PYTHON_FILES_EXPLANATION.md
  backend/tests/test_api.py
  backend/tests/common/**
  README.md
  docs/PROPOSAL.md
  docs/REPORT.md
  docs/PRESENTATION_AND_DEMO.md
  docs/TEST_ACCEPTANCE.md
  docs/notes/C.md
  docs/notes/C-ai-usage.md
  docs/requests/devC.md
  ```
- **Contracts Used:**
  - Consumes frozen backend endpoints via `frontend/src/services/api/client.ts` and `frontend/src/types.ts`.
  - Uses mock data in `frontend/src/data.ts` and `frontend/src/services/mocks/` whenever backend is offline or in development.
- **Definition of Done (DoD):**
  1. `npm run lint --prefix frontend` and `npm run build --prefix frontend` both exit 0 with 0 errors.
  2. `pytest backend/tests/test_api.py backend/tests/common/ -v` passes with 0 failures.
  3. Responsive UI verified on mobile ($375\times812$) and desktop ($1440\times900$) viewports.
  4. All capstone documents (`REPORT.md`, `PRESENTATION_AND_DEMO.md`, `PROPOSAL.md`) complete with 12 User Stories and complete Traceability Matrix.
  5. `python scripts/check_ownership.py --owner devC` exits 0 with 0 boundary violations.
  6. Notes documented in `docs/notes/C.md` and AI prompts logged in `docs/notes/C-ai-usage.md`.
- **Demo Script (3–5 min):**
  1. Demonstrate OAuth2 role switcher in `Header.tsx`: switch between Customer (`an.nguyen@company.vn`) and Admin (`admin@smartdesk.ai`).
  2. In Customer Chat: ask a query and show real-time SSE token typing, citation badges, and confirmation action card.
  3. In Agent Dashboard: show server-side sorting, priority filter, pagination, and ticket deletion.
  4. In Telemetry tab: show live token cost gauge, latency chart, and 1-click circuit breaker reset.
  5. In Knowledge Manager: show 3-agent verification trace log (`SyntheticQAExamAgent` $\to$ `SandboxRAGAgent` $\to$ `FaithfulnessJudgeAgent`).

---

### 2.4 Integrator Hat (Hoang / Dev B) — Architecture Governance & Release Coordination
- **Mission:** Guard frozen contracts, manage shared infrastructure files, review PRs, execute full integration test runs, and manage deployment releases.
- **Exclusive Owned Paths:**
  ```text
  .agents/**
  .cursorrules
  .env.example
  .gitattributes
  .github/**
  .gitignore
  AGENTS.md
  AI_USAGE.md
  backend/.env.example
  backend/README.md
  backend/pytest.ini
  backend/requirements.txt
  backend/app/__init__.py
  backend/app/api/__init__.py
  backend/app/api/v1/__init__.py
  backend/app/api/v1/api.py
  backend/app/core/__init__.py
  backend/app/core/config.py
  backend/app/core/exceptions.py
  backend/app/db/__init__.py
  backend/app/main.py
  backend/app/models/__init__.py
  backend/app/schemas/__init__.py
  backend/app/services/__init__.py
  backend/tests/__init__.py
  backend/tests/conftest.py
  docs/API_CONTRACT.md
  docs/ARCHITECTURE.md
  docs/DESIGN.md
  docs/DEV_START_HERE.md
  docs/adr/**
  docs/audit/**
  docs/implementation_plan_smartdesk_ai_upgrade.md
  docs/plan/**
  docs/requests/template.md
  docs/spec/**
  frontend/.env.example
  frontend/Dockerfile
  frontend/nginx.conf
  frontend/index.html
  frontend/package-lock.json
  frontend/package.json
  frontend/src/types.ts
  frontend/src/types/**
  frontend/src/services/api.ts
  frontend/src/services/api/client.ts
  frontend/src/services/api/index.ts
  frontend/tsconfig.json
  frontend/vite.config.ts
  pytest.ini
  scripts/check_ownership.py
  scripts/gen_codeowners.py
  scripts/ownership_map.py
  scripts/install.bat
  scripts/start.bat
  scripts/start_all.bat
  scripts/start_backend.bat
  scripts/verify_setup.ps1
  smartdesk_audit_report.md
  ```
- **Definition of Done (DoD):**
  1. `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1` reports `ALL 9/9 CHECKS PASSED`.
  2. `python scripts/check_ownership.py --verify-consistency` reports 0 conflicts across all workstreams.
  3. Clean git log with atomic conventional commits.

---

## 3. Master File-to-Owner Mapping Table

Every tracked file in the repository + planned new files is mapped to exactly **ONE** owner.

| File Path | Owner | Reason / Module Domain |
| :--- | :--- | :--- |
| `.agents/*` | Integrator | Skill and agent instructions |
| `.cursorrules` | Integrator | Repository governance & IDE guidelines |
| `.env.example` | Integrator | Shared environment template |
| `.gitattributes` | Integrator | Line-ending and Git attributes |
| `.github/*` | Integrator | GitHub branch protection & ownership |
| `.gitignore` | Integrator | Git ignore patterns |
| `AGENTS.md` | Integrator | Master AI rules and project governance |
| `AI_USAGE.md` | Integrator | Group AI usage log & compliance record |
| `Modelfile` | Dev A | Ollama local model specification |
| `README.md` | Dev C | User-facing documentation & quickstart guide |
| `docker-compose.yml` | Dev B | Multi-container infrastructure orchestration |
| `scripts/check_ownership.py` | Integrator | Pre-commit ownership validation tool |
| `scripts/gen_codeowners.py` | Integrator | CODEOWNERS generation script |
| `scripts/ownership_map.py` | Integrator | Single source of truth ownership map |
| `scripts/install.bat` | Integrator | Windows installation batch runner |
| `scripts/start.bat` | Integrator | Windows startup batch script |
| `scripts/start_all.bat` | Integrator | Windows multi-process startup runner |
| `scripts/start_backend.bat` | Integrator | Windows backend startup runner |
| `scripts/verify_setup.ps1` | Integrator | Universal 9-gate environment verifier |
| `backend/.env.example` | Integrator | Backend environment configuration template |
| `backend/Dockerfile` | Dev B | Backend container Dockerfile |
| `backend/PYTHON_FILES_EXPLANATION.md` | Dev C | Architecture file explanation guide |
| `backend/README.md` | Integrator | Backend technical documentation |
| `backend/pytest.ini` | Integrator | Pytest test configuration |
| `backend/requirements.txt` | Integrator | Python shared dependency declarations |
| `backend/data/prompts.json` | Dev A | Externalized prompt templates (v2.1) |
| `backend/data/seed_faq.json` | Dev A | Seed FAQ dataset for BM25 fallback |
| `backend/data/finetune_alpaca.jsonl` | Dev A | Fine-tuning dataset |
| `backend/data/sample_documents/*` | Dev A | Document samples for verification |
| `backend/data/eval_dataset.json` | Dev A | 24-case AI benchmark evaluation dataset |
| `backend/scripts/run_eval.py` | Dev A | AI evaluation benchmark test runner |
| `backend/scripts/export_finetune_dataset.py` | Dev A | Fine-tuning dataset export utility |
| `backend/scripts/reembed_chunks.py` | Dev B | Vector re-embedding migration utility |
| `backend/app/__init__.py` | Integrator | Python package marker |
| `backend/app/main.py` | Integrator | FastAPI ASGI application entrypoint |
| `backend/app/api/__init__.py` | Integrator | Python package marker |
| `backend/app/api/v1/__init__.py` | Integrator | Python package marker |
| `backend/app/api/v1/api.py` | Integrator | Master APIRouter registration |
| `backend/app/core/__init__.py` | Integrator | Python package marker |
| `backend/app/core/config.py` | Integrator | Global application settings & env loader |
| `backend/app/core/exceptions.py` | Integrator | Core exception handlers |
| `backend/app/core/prompts.py` | Dev A | Dynamic prompt loader & hot-reloader |
| `backend/app/core/deps.py` | Dev B | Auth & database dependency injections |
| `backend/app/core/security.py` | Dev B | Security sanitizer, PII redactor & JWT tools |
| `backend/app/db/__init__.py` | Integrator | Python package marker |
| `backend/app/db/base.py` | Dev B | SQLAlchemy declarative base |
| `backend/app/db/session.py` | Dev B | Database engine, session maker & migrations |
| `backend/app/db/seed/__init__.py` | Dev B | Database seeding barrel export |
| `backend/app/db/seed/seed_ai_usage.py` | Dev B | Initial AI usage seed data |
| `backend/app/db/seed/seed_tickets.py` | Dev B | Initial tickets seed data |
| `backend/app/db/seed/seed_users.py` | Dev B | Initial users seed data |
| `backend/app/models/__init__.py` | Integrator | SQLAlchemy model barrel export |
| `backend/app/models/user.py` | Dev B | User ORM model & RBAC enum |
| `backend/app/models/ticket.py` | Dev B | Ticket ORM model & status/priority enums |
| `backend/app/models/knowledge.py` | Dev B | Knowledge chunk ORM model with `pgvector` |
| `backend/app/models/workspace.py` | Dev B | Workspace ORM model & persona settings |
| `backend/app/models/document.py` | Dev B | Document metadata ORM model |
| `backend/app/models/verification.py` | Dev B | Verification report ORM model |
| `backend/app/models/ai_usage.py` | Dev B | AI request telemetry log ORM model |
| `backend/app/schemas/__init__.py` | Integrator | Schema barrel export |
| `backend/app/schemas/ai_structured.py` | Dev A | Pydantic structured output models |
| `backend/app/schemas/chat.py` | Dev A | Chat request, response & SSE schemas |
| `backend/app/schemas/verification.py` | Dev A | Verification request & report schemas |
| `backend/app/schemas/ticket.py` | Dev B | Ticket request & response schemas |
| `backend/app/schemas/workspace.py` | Dev B | Workspace schemas |
| `backend/app/schemas/document.py` | Dev B | Document upload & chunking schemas |
| `backend/app/schemas/health.py` | Dev B | Health schemas |
| `backend/app/schemas/knowledge.py` | Dev B | Knowledge schemas |
| `backend/app/schemas/auth.py` | Dev B | OAuth2 & JWT token schemas |
| `backend/app/services/__init__.py` | Integrator | Services barrel export |
| `backend/app/services/llm_service.py` | Dev A | Gemini/Ollama dual-provider LLM service |
| `backend/app/services/rag_service.py` | Dev A | Grounded RAG retrieval & generation service |
| `backend/app/services/ticket_copilot_service.py` | Dev A | AI triage & draft generation service |
| `backend/app/services/verification_service.py` | Dev A | Multi-agent active verification service |
| `backend/app/services/agent_tools.py` | Dev A | 4 agent tools & confirmation schema |
| `backend/app/services/ticket_service.py` | Dev B | Ticket CRUD, SLA mapping & filtering |
| `backend/app/services/document_service.py` | Dev B | Document text extraction & chunking |
| `backend/app/services/embedding_service.py` | Dev B | Vector embeddings & pgvector search |
| `backend/app/services/fallback_service.py` | Dev B | BM25 deterministic non-AI fallback |
| `backend/app/services/ai_usage_logger.py` | Dev B | Background async AI telemetry logger |
| `backend/app/api/v1/endpoints/chat.py` | Dev A | `/chat` endpoint |
| `backend/app/api/v1/endpoints/chat_stream.py` | Dev A | `/chat/stream` SSE endpoint |
| `backend/app/api/v1/endpoints/chat_actions.py` | Dev A | `/chat/confirm-action` endpoint |
| `backend/app/api/v1/endpoints/ai_usage.py` | Dev A | `/agent/ai-usage` telemetry endpoints |
| `backend/app/api/v1/endpoints/knowledge.py` | Dev A | `/knowledge` endpoints |
| `backend/app/api/v1/endpoints/tickets.py` | Dev B | `/tickets` CRUD & filter endpoints |
| `backend/app/api/v1/endpoints/agent.py` | Dev B | `/agent` triage endpoints |
| `backend/app/api/v1/endpoints/workspaces.py` | Dev B | `/workspaces` endpoints |
| `backend/app/api/v1/endpoints/documents.py` | Dev B | `/documents` & upload endpoints |
| `backend/app/api/v1/endpoints/auth.py` | Dev B | `/auth` OAuth2/JWT endpoints |
| `backend/app/api/v1/endpoints/health.py` | Dev B | `/health` system health endpoint |
| `backend/tests/__init__.py` | Integrator | Python test package marker |
| `backend/tests/conftest.py` | Integrator | Pytest global test fixtures & client setup |
| `backend/tests/test_rag_module.py` | Dev A | RAG pipeline unit tests |
| `backend/tests/test_ollama_provider.py` | Dev A | Local Ollama provider tests |
| `backend/tests/ai/*` | Dev A | AI structured output & agent tool tests |
| `backend/tests/test_tickets_module.py` | Dev B | Ticket service & CRUD tests |
| `backend/tests/test_auth_module.py` | Dev B | OAuth2, JWT & RBAC tests |
| `backend/tests/test_workspace_and_verification.py` | Dev B | Workspace & verification tests |
| `backend/tests/platform/*` | Dev B | Platform, pgvector & DB migration tests |
| `backend/tests/test_api.py` | Dev C | End-to-end API integration tests |
| `backend/tests/common/*` | Dev C | Cross-feature scenario tests |
| `frontend/.env.example` | Integrator | Frontend environment configuration template |
| `frontend/Dockerfile` | Integrator | Multi-stage production container Dockerfile (Frozen) |
| `frontend/nginx.conf` | Integrator | Nginx reverse proxy configuration (Frozen) |
| `frontend/index.html` | Integrator | Frontend HTML template entrypoint |
| `frontend/package.json` | Integrator | Frontend npm dependencies & build scripts |
| `frontend/package-lock.json` | Integrator | Frontend lockfile |
| `frontend/tsconfig.json` | Integrator | TypeScript root compiler configuration |
| `frontend/vite.config.ts` | Integrator | Vite bundler configuration |
| `frontend/metadata.json` | Dev C | Project UI metadata |
| `frontend/src/main.tsx` | Dev C | React DOM root mounting |
| `frontend/src/App.tsx` | Dev C | Top-level application coordinator |
| `frontend/src/index.css` | Dev C | Tailwind CSS styles |
| `frontend/src/data.ts` | Dev C | Local fallback mock data & offline logic |
| `frontend/src/components/*` | Dev C | Core UI views (Header, Chat, TicketForm, etc.) |
| `frontend/src/features/*` | Dev C | Modular feature components (chat, agent, etc.) |
| `frontend/src/services/api/auth.ts` | Dev C | Auth API client methods |
| `frontend/src/services/api/chat.ts` | Dev C | Chat API client methods |
| `frontend/src/services/api/documents.ts` | Dev C | Document API client methods |
| `frontend/src/services/api/telemetry.ts` | Dev C | Telemetry API client methods |
| `frontend/src/services/api/tickets.ts` | Dev C | Ticket API client methods |
| `frontend/src/services/api/workspaces.ts` | Dev C | Workspace API client methods |
| `frontend/src/services/mocks/*` | Dev C | Offline fixture mocks |
| `frontend/src/types.ts` | Integrator | Frozen canonical TypeScript interfaces facade |
| `frontend/src/types/*` | Integrator | Modular TypeScript interface files |
| `frontend/src/services/api.ts` | Integrator | Frozen API client facade |
| `frontend/src/services/api/client.ts` | Integrator | Shared fetch client with timeout & error handling |
| `frontend/src/services/api/index.ts` | Integrator | API client barrel export |
| `docs/API_CONTRACT.md` | Integrator | Frozen API REST specifications |
| `docs/ARCHITECTURE.md` | Integrator | System architecture & ownership map |
| `docs/DESIGN.md` | Integrator | Design tokens & component specifications |
| `docs/DEV_START_HERE.md` | Integrator | Mandatory developer onboarding guide |
| `docs/PROPOSAL.md` | Dev C | User stories & traceability matrix |
| `docs/REPORT.md` | Dev C | Formal capstone project report (10-20 pages) |
| `docs/PRESENTATION_AND_DEMO.md` | Dev C | 15-slide deck & 8-min demo playbook |
| `docs/TEST_ACCEPTANCE.md` | Dev C | Acceptance test matrix & verification scripts |
| `docs/adr/*` | Integrator | Architecture Decision Records (ADR-001..004) |
| `docs/audit/*` | Integrator | Project audit, checklist & gap analysis |
| `docs/implementation_plan_smartdesk_ai_upgrade.md` | Integrator | Upgrade implementation plan |
| `docs/plan/*` | Integrator | Workstreams, Git workflow & dev prompts |
| `docs/spec/*` | Integrator | Internal interface contracts & schemas |
| `docs/notes/A.md` | Dev A | Dev A developer notes & decisions |
| `docs/notes/A-ai-usage.md` | Dev A | Dev A AI prompting & bug-fix log |
| `docs/notes/A-eval-report.md` | Dev A | Dev A AI evaluation benchmark report |
| `docs/notes/B.md` | Dev B | Dev B developer notes & decisions |
| `docs/notes/B-ai-usage.md` | Dev B | Dev B AI prompting & bug-fix log |
| `docs/notes/C.md` | Dev C | Dev C developer notes & decisions |
| `docs/notes/C-ai-usage.md` | Dev C | Dev C AI prompting & bug-fix log |
| `docs/requests/devA.md` | Dev A | Dev A cross-workstream change requests |
| `docs/requests/devB.md` | Dev B | Dev B cross-workstream change requests |
| `docs/requests/devC.md` | Dev C | Dev C cross-workstream change requests |
| `docs/requests/template.md` | Integrator | Change request template |
| `pytest.ini` | Integrator | Pytest test configuration |
| `smartdesk_audit_report.md` | Integrator | Audit summary report |

*Summary:* **All tracked files mapped.**  
- **Overlaps:** **0**  
- **Unowned files:** **0**

---

## 4. Requirement & Criteria Coverage Table

Every requirement from [`docs/audit/00-checklist.md`](../audit/00-checklist.md) is mapped to an owner and verifiable task.

| ID | Description | Weight | Assigned Owner | Primary Task |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | Team size (3 members) & real problem scope | CRIT-01 / CRIT-03 | Integrator | Governance & Spec |
| **REQ-02** | Core AI utility beyond pass-through chat | CRIT-03 (25%) | Dev A | `TASK-08`, `TASK-09` |
| **REQ-03** | React 19 + Vite frontend stack | CRIT-02 (15%) | Dev C | `TASK-06`, `TASK-07` |
| **REQ-04** | SSE token streaming in UI | CRIT-02 / CRIT-07 | Dev A (BE) / Dev C (UI) | `TASK-11` |
| **REQ-05** | FastAPI ASGI asynchronous backend | CRIT-02 (15%) | Dev B | Architecture Baseline |
| **REQ-06** | RESTful CRUD APIs secured with JWT | CRIT-02 (15%) | Dev B | `TASK-12`, `TASK-13` |
| **REQ-07** | Persistent DB & PostgreSQL `pgvector` | CRIT-02 (15%) | Dev B | `TASK-14` |
| **REQ-08** | Backend-only LLM calls & key hygiene | CRIT-02 / Penalty | Integrator | Clean `package.json` |
| **REQ-09** | OAuth2 login & RBAC (`admin`/`user`) | CRIT-02 (15%) | Dev B (BE) / Dev C (UI) | `TASK-12` |
| **REQ-10** | Real-time updates / SSE token streaming | CRIT-02 / CRIT-07 | Dev A (BE) / Dev C (UI) | `TASK-11` |
| **REQ-11** | Full-stack Docker Compose deployment | CRIT-02 / CRIT-05 | Integrator (Frozen FE) / Dev B | `TASK-14` |
| **REQ-12** | Core AI capabilities count ($\ge 3$ capabilities) | CRIT-03 (25%) | Dev A | `TASK-08`, `TASK-09` |
| **REQ-13** | Capability A: RAG over app data with sources | CRIT-03 (25%) | Dev A | Baseline / `TASK-02` |
| **REQ-14** | Capability B: Tool-using agent (4 tools + confirm) | CRIT-03 (25%) | Dev A (BE) / Dev C (UI) | `TASK-09` |
| **REQ-15** | Capability C: Pydantic Structured Output | CRIT-03 (25%) | Dev A | `TASK-08` |
| **REQ-16** | Capability D: Multimodal input (Doc/PDF extraction) | CRIT-03 (25%) | Dev B | `TASK-05` |
| **REQ-17** | Capability E: Multi-agent verification trace | CRIT-03 (25%) | Dev A (BE) / Dev C (UI) | `TASK-08` |
| **REQ-18** | Model choice rationale (Cloud + Local Ollama) | CRIT-04 (10%) | Dev A | `TASK-01` (ADR-001) |
| **REQ-19** | Externalized versioned prompts (`prompts.json`) | CRIT-04 (10%) | Dev A | `TASK-04` |
| **REQ-20** | 3 Mandatory guardrails (Injection, Scope, Fail) | CRIT-04 / CRIT-05 | Dev A & Dev B | `TASK-03` |
| **REQ-21** | 24-Case AI Evaluation benchmark & pass rate | CRIT-04 (10%) | Dev A | `TASK-15` |
| **REQ-22** | AI request logging, tokens & cost tracking | CRIT-04 (10%) | Dev B (BE) / Dev A (Log) | `TASK-10` |
| **REQ-23** | Deterministic non-AI fallback (BM25) | CRIT-04 (10%) | Dev B | Baseline / `TASK-02` |
| **REQ-24** | 12 User stories with acceptance criteria | CRIT-01 (15%) | Dev C | `TASK-17` |
| **REQ-25** | End-to-end requirement traceability table | CRIT-01 / CRIT-06 | Dev C | `TASK-17` |
| **REQ-26** | System architecture diagram (Mermaid) | CRIT-01 (15%) | Dev C | `TASK-17` |
| **REQ-27** | 4 Architecture Decision Records (ADRs) | CRIT-01 (15%) | Integrator | `TASK-01` |
| **REQ-28** | Complete `AI_USAGE.md` with failure case studies | CRIT-06 / Penalty | Integrator & All Devs | `TASK-01` |
| **REQ-29** | Module ownership & Git commit history | CRIT-06 (20%) | All Members | Workstream Execution |
| **REQ-30** | Full CRUD for main app data (Tickets/Workspaces) | CRIT-02 (15%) | Dev B (BE) / Dev C (UI) | `TASK-13` |
| **REQ-31** | Search, filter, server sort & pagination | CRIT-02 (15%) | Dev B (BE) / Dev C (UI) | `TASK-13` |
| **REQ-32** | File upload used as AI input | CRIT-02 / CRIT-03 | Dev B (BE) / Dev C (UI) | `TASK-05` |
| **REQ-33** | Admin AI Usage Telemetry Dashboard | CRIT-02 / CRIT-04 | Dev A (API) / Dev C (UI) | `TASK-10` |
| **REQ-34** | Responsive UI (Desktop & Mobile 375px) | CRIT-07 (5%) | Dev C | `TASK-07` |
| **REQ-35** | Persistent database storage | CRIT-02 (15%) | Dev B | Baseline & `TASK-14` |
| **REQ-36** | Input validation & user data isolation | CRIT-02 (15%) | Dev B | `TASK-12` |
| **REQ-37** | LLM data privacy policy & PII minimization | CRIT-01 / CRIT-04 | Dev B (Sec) / Dev C (Doc) | `TASK-03`, `TASK-17` |
| **REQ-38** | Unit tests for core business logic | CRIT-02 / CRIT-04 | Dev C & Dev B | `TASK-16` |
| **REQ-39** | README with Docker guide & test accounts | CRIT-02 / CRIT-05 | Dev C | `TASK-17` |
| **REQ-40** | Formal project report (PDF, 10–20 pages) | CRIT-01 / CRIT-04 | Dev C | `TASK-17` |
| **REQ-41** | 15-Slide deck & 3–5 min backup demo video | CRIT-05 (10%) | Dev C | `TASK-17` |
| **REQ-42** | 10-Minute live change readiness & defense | CRIT-05 / CRIT-06 | All Members | `TASK-17` Playbook |

---

## 5. Merge-Conflict Hunter Audit Summary & Resolutions

During the architectural audit, the Merge-Conflict Hunter identified 4 primary collision zones:

### 5.1 Collision 1: `ticket_service.py` Double Ownership
- **Problem:** Dev A needed `ticket_service.py` to inject `TicketCopilotStructuredOutput` (TASK-08), while Dev B needed it for database CRUD, user filtering, sorting, pagination, and SLA hours (TASK-10, 12, 13).
- **Resolution:** Split the file:
  - Dev B owns `backend/app/services/ticket_service.py` (pure DB operations, SLA hours, sorting, filtering).
  - Dev A owns `backend/app/services/ticket_copilot_service.py` (AI structured triage and draft generation).
  - Dev B imports `ticket_copilot_service` via the frozen interface defined in `CONTRACTS.md`. Result: **Zero collision**.

### 5.2 Collision 2: `endpoints/agent.py` vs `endpoints/ai_usage.py`
- **Problem:** `agent.py` previously housed both agent ticket copilot actions and AI usage telemetry stats.
- **Resolution:**
  - Dev B owns `backend/app/api/v1/endpoints/agent.py` (ticket copilot actions).
  - Dev A owns `backend/app/api/v1/endpoints/ai_usage.py` (telemetry stats & circuit breaker reset). Result: **Zero collision**.

### 5.3 Collision 3: `frontend/src/**` Workload Bottleneck
- **Problem:** If Dev C owns all frontend files, Dev A and Dev B might be blocked when testing their backend endpoints in the browser.
- **Resolution:** Dev A and Dev B write independent unit/integration tests with `pytest` and test endpoints via Swagger UI (`/docs`). Dev C owns all `frontend/src/**` UI files and wires them cleanly. Mock fixtures in `frontend/src/services/mocks/` decouple Dev C from backend completion.

### 5.4 Collision 4: Test Directory Collisions
- **Problem:** All developers adding tests to a single `test_api.py` would cause constant merge conflicts.
- **Resolution:** Partitioned test directories:
  - Dev A: `backend/tests/test_rag_module.py`, `test_ollama_provider.py`, and `backend/tests/ai/*`.
  - Dev B: `backend/tests/test_tickets_module.py`, `test_auth_module.py`, `test_workspace_and_verification.py`, and `backend/tests/platform/*`.
  - Dev C: `backend/tests/test_api.py` and `backend/tests/common/*`.
  - Integrator: `backend/tests/conftest.py` and `pytest.ini`. Result: **Zero collision**.
