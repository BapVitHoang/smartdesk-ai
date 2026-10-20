# SmartDesk AI – System Architecture & Module Ownership Guide (`ARCHITECTURE.md`)

> **Version:** 1.1.0 (Frozen Foundation Skeleton)  
> **Purpose:** Define the finalized repository layout, strict module ownership boundaries across 3 developers/agents, frozen shared contracts, and conflict-free extension points.

---

## 1. Finalized Repository Structure

```text
smartdesk-ai/
├── .agents/                          # AI Assistant rules & skills
│   ├── rules/                        # backend-standards.md, frontend-standards.md, security-and-fallback.md
│   └── skills/                       # fastapi-backend-builder, react-frontend-builder, qa-acceptance-tester
├── .github/workflows/
│   └── ci.yml                        # GitHub Actions CI (Frontend lint/build + Backend pytest)
├── backend/                          # FastAPI (Python 3.11+) Async Backend
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── api.py                # [SHARED] Central router registry with modular extension hooks
│   │   │   └── endpoints/            # One router file per domain module
│   │   │       ├── chat.py           # [Owner 1] POST /api/v1/chat
│   │   │       ├── documents.py      # [Owner 1] Upload, chunk inspection, 3-stage verification, publish
│   │   │       ├── knowledge.py      # [Owner 1] FAQ & knowledge retrieval
│   │   │       ├── tickets.py        # [Owner 2] Ticket CRUD & filtering
│   │   │       ├── agent.py          # [Owner 2] AI Copilot draft regeneration
│   │   │       ├── workspaces.py     # [Owner 2] Multi-domain workspace CRUD
│   │   │       └── health.py         # [Owner 2] Readiness & LLM latency smoke-test
│   │   ├── core/
│   │   │   ├── config.py             # [SHARED] Pydantic Settings (.env loader, SQLite path resolver)
│   │   │   ├── prompts.py            # [Owner 1] Versioned prompt template loader
│   │   │   ├── security.py           # [Owner 1] Input sanitizer & Prompt Injection guardrail
│   │   │   └── exceptions.py         # [SHARED] RFC 7807 structured exception classes & handlers
│   │   ├── db/
│   │   │   ├── base.py               # [Owner 2] SQLAlchemy 2.0 DeclarativeBase
│   │   │   └── session.py            # [Owner 2] Dual-engine async session (pgvector / SQLite) & seeding
│   │   ├── models/                   # [Owner 2] SQLAlchemy 2.0 ORM models
│   │   ├── schemas/                  # [SHARED] Frozen Pydantic v2 request/response contracts
│   │   ├── services/
│   │   │   ├── llm_service.py        # [Owner 1] Gemini 3.5/2.5 Flash Lite + Ollama + 429 Cost-Guard
│   │   │   ├── embedding_service.py  # [Owner 1] Gemini/Ollama embeddings + Dual-mode cosine search
│   │   │   ├── rag_service.py        # [Owner 1] Workspace-isolated RAG orchestrator
│   │   │   ├── fallback_service.py   # [Owner 1] Pure-Python Okapi BM25 deterministic matcher
│   │   │   ├── verification_service.py # [Owner 1] 3-stage Synthetic QA -> Self-Test -> AI Judge
│   │   │   ├── agent_tools.py        # [Owner 1] Tool registry & execution hook for Agentic workflows
│   │   │   ├── ticket_service.py     # [Owner 2] SLA calculation, auto-tagging, AI Copilot draft
│   │   │   └── document_service.py   # [Owner 2] PDF/TXT/MD text extraction & recursive chunker
│   │   └── main.py                   # [SHARED] FastAPI ASGI app factory, CORS, timing middleware
│   ├── data/
│   │   ├── prompts.json              # [Owner 1] Externalized, versioned system prompt catalog
│   │   ├── seed_faq.json             # [Owner 1] Curated 12-item FAQ dataset for BM25 fallback
│   │   └── sample_documents/         # [Owner 1] Domain sample docs (SmileCare, TechStore)
│   ├── scripts/                      # [Owner 1/2] CLI utilities (reembed_chunks.py, export_finetune_dataset.py)
│   └── tests/                        # Per-module automated Pytest suites
│       ├── test_api.py               # [SHARED] Core baseline integration tests (9 tests)
│       ├── test_workspace_and_verification.py # [Owner 1/2] Workspaces & verification pipeline (9 tests)
│       ├── test_ollama_provider.py   # [Owner 1] Dual AI provider unit tests (6 tests)
│       ├── test_rag_module.py        # [Owner 1] RAG, prompt loader & agent tools module tests
│       ├── test_tickets_module.py    # [Owner 2] Ticket SLA, categories & triage module tests
│       └── test_auth_module.py       # [Owner 2] Security guardrails & auth extension module tests
├── frontend/                         # React 19 + Vite 6 + Tailwind CSS v4 SPA
│   ├── src/
│   │   ├── components/               # [Owner 3] Core screen components
│   │   ├── features/                 # [Owner 3] Isolated feature subfolders (auth, telemetry, tools)
│   │   ├── services/
│   │   │   └── api.ts                # [SHARED] Central API client with offline fallback
│   │   ├── data.ts                   # [Owner 3] Local fallback mock dataset
│   │   ├── types.ts                  # [SHARED] Frozen TypeScript interfaces & domain enums
│   │   └── App.tsx                   # [SHARED] Root tab & state coordinator
│   ├── package.json
│   └── vite.config.ts
├── docs/                             # Governing specifications, ADRs, audit & plan
│   ├── adr/                          # ADR-001 .. ADR-004
│   ├── audit/                        # 00-checklist, 01-gap-analysis, 02-brainstorm-notes, 03-working-tree-triage
│   ├── plan/PLAN.md                  # Phased implementation roadmap
│   ├── spec/SPEC.md                  # Detailed technical specifications
│   ├── ARCHITECTURE.md               # This file
│   ├── API_CONTRACT.md               # Frozen REST API schemas
│   ├── DESIGN.md                     # UI/UX tokens & 4-state specifications
│   ├── PROPOSAL.md                   # 12 User Stories & Requirement Traceability Matrix
│   └── TEST_ACCEPTANCE.md            # Manual & automated acceptance test matrix
├── scripts/                          # Windows batch launchers (install.bat, start_all.bat, etc.)
├── AI_USAGE.md                       # AI usage disclosure & failure/fix case studies
├── AGENTS.md                         # Master rules for AI assistants & developers
└── docker-compose.yml                # PostgreSQL 16 (pgvector) + Backend container orchestration
```

---

## 2. Module Ownership Matrix (3-Developer / Workstream Boundaries)

To prevent merge conflicts during parallel development, every file in the repository belongs to exactly ONE designated owner:

| Developer / Role | Owned Backend Modules | Owned Frontend, Infra & Docs | Dedicated Test Suites |
| :--- | :--- | :--- | :--- |
| **Dev A (Owner 1: AI Engine Lead)** | `services/llm_service.py`, `rag_service.py`, `fallback_service.py`, `verification_service.py`, `agent_tools.py`, `core/prompts.py`, `endpoints/chat.py`, `chat_stream.py`, `chat_actions.py`, `knowledge.py`, `backend/data/*`, `backend/scripts/*`, `Modelfile` | `docs/notes/A.md`, `docs/notes/A-ai-usage.md`, `docs/requests/A.md` | `backend/tests/test_rag_module.py`, `test_ollama_provider.py`, `backend/tests/ai/*` |
| **Dev B (Owner 2: Platform & Data Lead)** | `services/ticket_service.py`, `document_service.py`, `embedding_service.py`, `ai_usage_logger.py`, `core/deps.py`, `core/security.py`, `db/base.py`, `session.py`, `seed/*`, `models/*`, `endpoints/tickets.py`, `agent.py`, `workspaces.py`, `documents.py`, `auth.py`, `ai_usage.py`, `health.py` | `docker-compose.yml`, `docs/notes/B.md`, `docs/notes/B-ai-usage.md`, `docs/requests/B.md` | `backend/tests/test_tickets_module.py`, `test_auth_module.py`, `test_workspace_and_verification.py`, `backend/tests/platform/*` |
| **Dev C (Owner 3: Frontend UX, QA & Docs Lead)** | `backend/Dockerfile`, `backend/PYTHON_FILES_EXPLANATION.md`, `backend/README.md` | `frontend/src/*`, `frontend/Dockerfile`, `frontend/nginx.conf`, `README.md`, `AI_USAGE.md`, `docs/DESIGN.md`, `docs/PROPOSAL.md`, `docs/TEST_ACCEPTANCE.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/adr/*`, `docs/audit/*`, `docs/notes/*`, `scripts/*.bat` | `backend/tests/test_api.py`, `backend/tests/common/*` |
| **Integrator / Hoang (Shared Gatekeeper)** | `api/v1/api.py`, `core/config.py`, `core/exceptions.py`, `schemas/*`, `models/__init__.py`, `requirements.txt`, `.env.example`, `conftest.py`, `pytest.ini` | `frontend/package*.json`, `tsconfig.json`, `vite.config.ts`, `types.ts`, `types/index.ts`, `services/api.ts`, `services/api/index.ts`, `services/api/client.ts`, `docs/spec/CONTRACTS.md`, `docs/API_CONTRACT.md`, `AGENTS.md`, `.cursorrules`, `.gitattributes`, `.gitignore`, `.github/**`, `scripts/check_ownership.py`, `scripts/verify_setup.ps1` | All shared test fixtures |

### Strict Collaboration Rules
1. **Do Not Edit Outside Your Module:** An agent or developer assigned to a task for Owner 1 must not modify Owner 2's services or Owner 3's UI components unless explicitly designated as an integration task.
2. **Shared File Freeze:** Shared contract files (`api.py`, `config.py`, `schemas/*`, `types.ts`, `services/api.ts`, `App.tsx`, `API_CONTRACT.md`) are frozen. Adding a new endpoint router works automatically via optional router discovery in `backend/app/api/v1/api.py` without conflicting edits.
3. **Test Isolation:** Add new unit/integration tests to your module's dedicated test file (`test_rag_module.py`, `test_tickets_module.py`, `test_auth_module.py`) rather than appending to `test_api.py`.

---

## 3. Clean Extension Points

1. **Dynamic Router Registration (`backend/app/api/v1/api.py`):** Automatically mounts optional routers (`app.api.v1.endpoints.auth`, `app.api.v1.endpoints.telemetry`) if present, avoiding merge conflicts in `api.py`.
2. **Externalized Prompt Catalog (`backend/app/core/prompts.py` + `backend/data/prompts.json`):** Centralizes versioned prompts (`rag_customer_support`, `ticket_copilot_draft`, `verification_synthetic_qa`, `verification_ai_judge`) with safe fallback defaults.
3. **Agent Tool Registry (`backend/app/services/agent_tools.py`):** Provides a typed `ToolDefinition` and `AgentToolRegistry` interface for registering read/write support tools (`lookup_ticket_status`, `calculate_sla_deadline`, `escalate_ticket_priority`) without coupling to `rag_service.py`.
4. **Frontend Feature Modules (`frontend/src/features/`):** Dedicated extension directory for new self-contained UI panels (`auth`, `telemetry`, `tools`).
