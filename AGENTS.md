# SmartDesk AI - Rules & Guidelines for AI Assistant

This file outlines the foundational technical rules, architecture constraints, module ownership boundaries, and coding standards that every developer and AI assistant must strictly follow when working on **SmartDesk AI**.

---

## 1. Project Context & Mandatory Document Index

### 1.1 Core Architecture
- **System Name:** SmartDesk AI (Intelligent Customer Support & Knowledge Synthesizer).
- **Frontend:** React 19 + Vite 6 + Tailwind CSS v4 + TypeScript + Lucide Icons + Motion (Single Page Application, NOT Next.js).
- **Backend:** FastAPI (Python 3.11+) asynchronous ASGI service.
- **Database:** PostgreSQL 16 with `pgvector` (Fallback: Async SQLite `aiosqlite` with in-Python cosine similarity for local development/testing).
- **Primary Cloud LLM:** Google Gemini GA `gemini-3.5-flash-lite` (verified available on Google API; minimal thinking budget `thinking_budget=0` to ensure < 1,500ms latency), embeddings via `gemini-embedding-001`. Optional `LLM_FALLBACK_MODEL` env var (empty by default; no silent rewriting). Real token cost tracking: input $0.30/1M, output $2.50/1M.
- **Local AI Provider (Dual-Mode):** Ollama (`qwen2.5:3b` + `nomic-embed-text`) via `AI_PROVIDER=ollama`.
- **Deterministic Non-AI Fallback:** Pure-Python Okapi BM25 FAQ matcher on curated dataset (`backend/data/seed_faq.json`) + deterministic SHA-256 768-dim unit pseudo-embeddings when offline or rate-limited.
- **Team Size:** 3 Developers (Dev A / Owner 1, Dev B / Owner 2, Dev C / Owner 3 + Integration Owner).

### 1.2 Mandatory Document Reference Index
Before implementing any task, the AI assistant MUST consult the following canonical documents:
1. **System Architecture & Module Ownership:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - Folder ownership, shared files policy, and extension points.
2. **API Specifications & Schemas:** [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md) - Full request/response schemas, error codes, and HTTP status contracts.
3. **Internal Interface Contracts:** [`docs/spec/CONTRACTS.md`](./docs/spec/CONTRACTS.md) - Frozen signatures for dependencies, structured AI schemas, and logging stubs.
4. **UI/UX & Design Tokens:** [`docs/DESIGN.md`](./docs/DESIGN.md) - Brand colors, typography hierarchy, UI state handling, and component specs.
5. **Acceptance Test Matrix:** [`docs/TEST_ACCEPTANCE.md`](./docs/TEST_ACCEPTANCE.md) - Core acceptance test scenarios and automated verification instructions.
6. **Project Proposal & Traceability:** [`docs/PROPOSAL.md`](./docs/PROPOSAL.md) - User stories (`US-01..US-12`) and Requirement Traceability Matrix.
7. **AI Usage & Verification Log:** [`AI_USAGE.md`](./AI_USAGE.md) & [`docs/adr/`](./docs/adr/) - AI collaboration log and Architecture Decision Records (`ADR-001..004`).
8. **General Overview & Startup:** [`README.md`](./README.md) - Quickstart guide and Windows batch script definitions (`scripts/start.bat`, `scripts/start_all.bat`, `scripts/start_backend.bat`, `scripts/install.bat`).

---

## 2. Strict Frontend Architecture Rules

### 2.1 Code Structure & Organization
All frontend code is structured under `frontend/src/`:
```text
frontend/src/
├── components/                  # Core views & shared navigation (thin coordinators)
│   ├── Header.tsx               # Top navigation, active tab switcher, demo state switcher
│   ├── ChatView.tsx             # Customer RAG chat, citation badges, workspace selector
│   ├── TicketFormView.tsx       # Ticket submission form, SLA preview, live validation
│   ├── AgentDashboardView.tsx   # Agent triage table, filtering, AI copilot draft review
│   ├── KnowledgeManagerView.tsx # Workspace persona config, doc upload, AI verification studio
│   └── Footer.tsx               # System status badge, latency summary, copyright
├── features/                    # Modular feature components ("Stay in Your Lane")
│   ├── agent/                   # TicketToolbar, TicketList, TicketDetail (Owner 2)
│   ├── auth/                    # LoginSwitcher, UserProfileBadge (Owner 2)
│   ├── chat/                    # CitationBadge, ChatMessageList (Owner 1)
│   ├── knowledge/               # VerificationTrace, DocumentUploader (Owner 2)
│   └── telemetry/               # TelemetryPanel, CostGuardGauge (Owner 1)
├── services/
│   ├── api/                     # Modular API client services
│   │   ├── client.ts            # Base URL, fetchWithTimeout, auth headers, ApiError
│   │   ├── chat.ts              # RAG query & SSE token streaming (Owner 1)
│   │   ├── tickets.ts           # Ticket creation, filtering, triage & SLA mapping (Owner 2)
│   │   ├── workspaces.ts        # Workspace persona management (Owner 2)
│   │   ├── documents.ts         # Document upload, chunking & active verification (Owner 2)
│   │   ├── auth.ts              # Hybrid OAuth2 & demo authentication (Owner 2)
│   │   ├── telemetry.ts         # Token usage & cost-guard stats (Owner 1)
│   │   └── index.ts             # Central API client barrel export
│   ├── api.ts                   # Central API client facade (FROZEN CONTRACT)
│   └── mocks/                   # Fixture mocks for local offline development (Owner 3)
├── types/                       # Modular TypeScript definitions
│   ├── common.ts                # TabType, UIState, DemoState, Toast
│   ├── chat.ts                  # Citation, ChatMessage, BackendChatResponse
│   ├── ticket.ts                # Ticket, TicketFormData, BackendTicketResponse
│   ├── workspace.ts             # Workspace model
│   ├── document.ts              # KnowledgeArticle, DocumentItem, VerificationReport
│   ├── auth.ts                  # User, UserRole, AuthTokenResponse
│   ├── telemetry.ts             # AIUsageStats, AIUsageLogItem
│   └── index.ts                 # Central types barrel export
├── types.ts                     # Canonical TypeScript interfaces facade (FROZEN CONTRACT)
├── data.ts                      # Local fallback mock dataset & deterministic RAG fallback
└── App.tsx                      # Main application coordinator & active tab state management
```

### 2.2 Frontend State & API Client Rules
- **Centralized API Calls:** NEVER call `fetch()` or `axios` directly inside UI components. ALL network calls must go through [`frontend/src/services/api/`](./frontend/src/services/api/) or the facade [`frontend/src/services/api.ts`](./frontend/src/services/api.ts).
- **Dual-Mode Graceful Fallback:** If the backend API is offline or unreachable (`TypeError` / network timeout):
  1. Do NOT crash the application or display unhandled blank screens.
  2. Automatically fallback to local data in `frontend/src/data.ts` (`INITIAL_TICKETS`, `getRagResponse`).
  3. Trigger a non-blocking toast warning (`notifyFallback`) to notify the user.
  4. Do NOT swallow intentional HTTP 4xx security/validation errors (e.g., HTTP 400 `PROMPT_SECURITY_VIOLATION` or HTTP 401/403).
- **Language Convention:**
  - **User Interface:** All customer and agent visible labels, placeholders, tooltips, and toast messages must be in **Vietnamese**.
  - **Code & Comments:** Variable names, function names, TypeScript types, and code comments must be in **English**.

### 2.3 UI/UX & Tailwind CSS v4 Guidelines
- Strictly utilize design tokens from [`docs/DESIGN.md`](./docs/DESIGN.md):
  - Brand Primary: `indigo-600` (`#4F46E5`), Hover: `indigo-700` (`#4338CA`)
  - AI Badges / Thinking: `violet-500` (`#8B5CF6`)
  - Caution / Fallback: `amber-500` (`#F59E0B`)
  - Danger / Urgent: `rose-600` (`#E11D48`)
  - Success / Resolved: `emerald-600` (`#059669`)
- Ensure all 4 interaction states are gracefully handled in every view: `Loading`, `Empty`, `Success`, and `Error / Fallback`.

---

## 3. Strict Backend Architecture Rules

### 3.1 Code Structure & Organization
All backend source code is structured under `backend/app/`:
```text
backend/app/
├── core/         # Settings (config.py), externalized prompts (prompts.py), security, deps.py (auth dependencies)
├── db/           # Async database session (session.py), declarative Base (base.py) & seed/ (modular seeders)
├── models/       # SQLAlchemy 2.0 ORM models (Ticket, FAQItem, KnowledgeChunk, Workspace, Document, Verification, User, AIUsageLog)
├── schemas/      # Pydantic v2 schemas for Request/Response validation & ai_structured.py (FROZEN CONTRACT)
├── services/     # Business logic (RAG, LLM, Embedding, Fallback, Ticket Copilot, Document, Verification, Agent Tools, AI Usage Logger)
└── api/v1/       # FastAPI APIRouters (chat, chat_stream, chat_actions, tickets, agent, knowledge, workspaces, documents, auth, ai_usage, health)
```

### 3.2 Async/Await & Concurrency
- **Mandatory Async:** All I/O operations (database queries, network requests, Gemini/Ollama API calls) MUST use `async` / `await`. Never block the ASGI event loop with synchronous HTTP calls (`requests.get()` or `time.sleep()`).
- **Connection Pooling:** Database sessions must be managed via FastAPI `Depends(get_db)` yielding async sessions. Background scripts must access `db_session.async_session_factory` via module reference.

### 3.3 Strict Typing & Validation
- **Python Type Hints:** Every function, method parameter, and return value must have explicit type annotations (`from typing import Optional, List, Dict, Any`).
- **Pydantic v2:** All external inputs and outputs must pass through Pydantic v2 models. Never accept raw unvalidated dicts in route handlers.

---

## 4. AI, RAG & Fallback Constraints

### 4.1 Latency Budget & Cost-Guard Circuit Breaker
- **Latency Target:** First token / simple query response target is **< 1,500ms** (p95 < 2,000ms).
- **Timeout Threshold:** External calls to Google Gemini API must timeout at **4.0 seconds max** (`LLM_TIMEOUT_SECONDS=4.0`).
- **Model Fallback Chain:**
  1. Primary Cloud LLM: `gemini-3.5-flash-lite` with minimal thinking budget (`thinking_budget=0`).
  2. Local LLM Mode: `qwen2.5:3b` via Ollama when `AI_PROVIDER=ollama`.
  3. Deterministic Non-AI Fallback: If the LLM call times out, returns HTTP 429 (`ResourceExhausted`), or encounters an exception, activate the 60s Cost-Guard cooldown (`cooldown_until = now + 60s`), route immediately to `FallbackService` (BM25 matcher on `seed_faq.json`), and return `"is_fallback": true`.

### 4.2 Grounding, Prompt Management & Safety
- **Externalized Prompts:** System prompts are versioned in `backend/data/prompts.json` and loaded via `backend/app/core/prompts.py`.
- **System Prompt Constraint:** Enforce `temperature: 0.2` for customer-facing RAG. Instruct the model strictly to answer only from provided context or recommend escalating to a human support agent.
- **Citation Badges:** Every RAG-generated answer must extract and return structured source citations (`doc_id`, `title`, `source_url`, `page`, `snippet`).
- **Security & Guardrails:** Incoming queries must pass through `core/security.py` (`sanitize_input`, `check_prompt_injection`). If prompt injection is detected, reject immediately with HTTP 400 (`PROMPT_SECURITY_VIOLATION`). PII (emails, phone numbers, CCCD/IDs) must be redacted before sending to external cloud models.

---

## 5. Ticket Lifecycle, Categories, SLA & Status Mapping Rules

### 5.1 Canonical ID, Priority, Category & SLA Rules
- **Ticket ID Format:** Must follow `#TICK-XXXX` format (e.g., `#TICK-1042`).
- **Urgency / Priority Levels & Canonical SLA Hours:**
  - `Urgent`: **2 hours**
  - `High`: **4 hours**
  - `Medium`: **8 hours**
  - `Low`: **24 hours**
- **Canonical Categories:** `"Authentication"`, `"Billing"`, `"Bug Report"`, `"Feature Request"`, `"General"`.
  - *Alias Rule:* Backend accepts `"Technical Bug"` as a backward-compatible alias and normalizes it to `"Bug Report"`.

### 5.2 Status Mapping Between Backend and Frontend
| Lifecycle Phase | Backend Status (DB/API) | Frontend Status (UI/Types) | Color Badge |
| :--- | :--- | :--- | :--- |
| Initial Submission | `"open"` | `"Open"` | Blue (`sky-500`) |
| Under Review / Triaged | `"in_progress"` | `"Pending"` | Amber (`amber-500`) |
| Solved & Approved | `"resolved"` | `"Resolved"` | Emerald (`emerald-600`) |

---

## 6. Multi-Agent & Team Collaboration Rules (Strict Conflict Prevention)

1. **Role Mapping & Module Ownership Boundaries (Team of Exactly 3 Members):**
   - **Team Composition:**
     - **Dev A / Owner 1 (AI Engine & QA):** `@TheOrijinnn`
     - **Dev B / Owner 2 & Integrator (Platform, Security & Shared Contracts):** `@BapVitHoang` (Hoang wears both the Dev B hat and the Integrator hat)
     - **Dev C / Owner 3 (Frontend UX, QA & Documentation):** `@[C_USERNAME]`
   - **Dev A / Owner 1 (AI Engine, RAG, Structured Output, Guardrails & Eval):**
     - Owns `backend/app/services/llm_service.py`, `rag_service.py`, `ticket_copilot_service.py`, `verification_service.py`, `agent_tools.py`.
     - Owns `backend/app/core/prompts.py`, `backend/app/api/v1/endpoints/chat.py`, `chat_stream.py`, `chat_actions.py`, `knowledge.py`, `ai_usage.py`.
     - Owns `backend/app/schemas/ai_structured.py`, `chat.py`, `verification.py`.
     - Owns `backend/data/prompts.json`, `seed_faq.json`, `finetune_alpaca.jsonl`, `sample_documents/*`, `eval_dataset.json`.
     - Owns `backend/scripts/run_eval.py`, `export_finetune_dataset.py`, `Modelfile`.
     - Owns `backend/tests/test_rag_module.py`, `test_ollama_provider.py`, `backend/tests/ai/*`.
     - Owns `docs/notes/A.md`, `docs/notes/A-ai-usage.md`, `docs/notes/A-eval-report.md`, `docs/requests/devA.md`.
   - **Dev B / Owner 2 (Platform, Auth, Database, Workspaces, Tickets & Docker DB):**
     - Owns `backend/Dockerfile`, `backend/app/services/ticket_service.py`, `document_service.py`, `embedding_service.py`, `fallback_service.py`, `ai_usage_logger.py`.
     - Owns `backend/app/core/deps.py`, `backend/app/core/security.py`.
     - Owns `backend/app/db/base.py`, `session.py`, `seed/*`, `models/*`.
     - Owns `backend/app/schemas/ticket.py`, `workspace.py`, `document.py`, `health.py`, `knowledge.py`, `auth.py`.
     - Owns `backend/app/api/v1/endpoints/tickets.py`, `agent.py`, `workspaces.py`, `documents.py`, `auth.py`, `health.py`.
     - Owns `backend/scripts/reembed_chunks.py`.
     - Owns `backend/tests/test_tickets_module.py`, `test_auth_module.py`, `test_workspace_and_verification.py`, `backend/tests/platform/*`.
     - Owns `docker-compose.yml`, `docs/notes/B.md`, `docs/notes/B-ai-usage.md`, `docs/requests/devB.md`.
   - **Dev C / Owner 3 (Frontend UX, Mocks, QA Tests & Capstone Documentation):**
     - Owns `frontend/src/*` (components, features, services/api, services/mocks, data.ts, App.tsx, main.tsx, index.css, metadata.json).
     - Owns `backend/PYTHON_FILES_EXPLANATION.md`.
     - Owns `backend/tests/test_api.py`, `backend/tests/common/*`.
     - Owns `README.md`, `docs/PROPOSAL.md`, `docs/TEST_ACCEPTANCE.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/notes/C.md`, `docs/notes/C-ai-usage.md`, `docs/requests/devC.md`.
   - **Integrator Hat (Hoang / Dev B) (Architecture, Shared Contracts & Integration Reviewer):**
     - Exclusively owns `backend/app/core/config.py`, `backend/app/core/exceptions.py`, `backend/requirements.txt`, `backend/.env.example`.
     - Exclusively owns `backend/app/api/v1/api.py`, `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`, `backend/app/services/__init__.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `pytest.ini`, `backend/README.md`.
     - Exclusively owns `frontend/.env.example`, `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/index.html`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`.
     - Exclusively owns `frontend/src/types.ts`, `frontend/src/types/*`, `frontend/src/services/api.ts`, `frontend/src/services/api/index.ts`, `frontend/src/services/api/client.ts`.
     - Exclusively owns `AI_USAGE.md`, `docs/DESIGN.md`, `docs/DEV_START_HERE.md`, `docs/API_CONTRACT.md`, `docs/spec/*`, `docs/adr/*`, `docs/audit/*`, `docs/plan/*`, `docs/requests/template.md`, `AGENTS.md`, `.cursorrules`, `.gitattributes`, `.gitignore`, `.github/*`, `scripts/*`.
   - **Rule:** Do NOT edit files outside your assigned module without explicit coordination.
2. **Frozen Shared Files Policy:**
   - Frozen shared integration files may ONLY be modified through the **Integration Owner** (Hoang).
   - To request a change to frozen files, create a request file in `docs/requests/<dev>.md` using `docs/requests/template.md`.
3. **Automated Ownership Verification:**
   - Run `python scripts/check_ownership.py --staged` before committing.
   - Any attempt to commit cross-module files or frozen shared files on a feature branch will be blocked with exit code 1.
4. **Git Branch & Commit Convention:**
   - Branch naming: `feature/a-ai-engine` (Dev A), `feature/b-platform` (Dev B), `feature/c-frontend-docs` (Dev C).
   - Daily rebase on `main` / integration branch.
   - Commit messages MUST follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
   - NEVER use `git push --force`, `git reset --hard`, or commit `.env` / `*.db` files.
5. **Mandatory Pre-Commit Verification Gate:**
   - Every commit MUST pass all checks with 0 errors before committing:
     - Verify environment & toolchain: `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1`
     - Backend: `python -m pytest backend/tests/ -v`
     - Frontend: `npm run lint --prefix frontend; npm run build --prefix frontend`
     - Ownership: `python scripts/check_ownership.py --staged`
