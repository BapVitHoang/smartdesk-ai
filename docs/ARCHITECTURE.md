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
│   │   │   ├── api.py                # [Integrator] Central router registry
│   │   │   └── endpoints/            # Domain endpoint routers
│   │   │       ├── chat.py           # [Dev A] POST /api/v1/chat
│   │   │       ├── chat_stream.py    # [Dev A] POST /api/v1/chat/stream SSE
│   │   │       ├── chat_actions.py   # [Dev A] POST /api/v1/chat/confirm-action
│   │   │       ├── ai_usage.py       # [Dev A] GET /api/v1/agent/ai-usage, reset-cooldown
│   │   │       ├── knowledge.py      # [Dev A] FAQ & knowledge chunk retrieval
│   │   │       ├── documents.py      # [Dev B] Upload, chunk inspection, 3-stage verification, publish
│   │   │       ├── tickets.py        # [Dev B] Ticket CRUD, sorting, pagination, delete
│   │   │       ├── agent.py          # [Dev B] AI Copilot draft regeneration
│   │   │       ├── workspaces.py     # [Dev B] Multi-domain workspace CRUD & deletion
│   │   │       ├── auth.py           # [Dev B] OAuth2 login, JWT token, /me
│   │   │       └── health.py         # [Dev B] Readiness & LLM latency smoke-test
│   │   ├── core/
│   │   │   ├── config.py             # [Integrator] Pydantic Settings (.env loader, SQLite path resolver)
│   │   │   ├── exceptions.py         # [Integrator] RFC 7807 structured exception classes & handlers
│   │   │   ├── prompts.py            # [Dev A] Versioned prompt template loader & hot-reload
│   │   │   ├── deps.py               # [Dev B] Auth dependencies & get_current_user
│   │   │   └── security.py           # [Dev B] Input sanitizer, PII redactor & Prompt Injection guardrail
│   │   ├── db/
│   │   │   ├── base.py               # [Dev B] SQLAlchemy 2.0 DeclarativeBase
│   │   │   ├── seed/                 # [Dev B] Modular database seeders
│   │   │   └── session.py            # [Dev B] Dual-engine async session (pgvector / SQLite) & migrations
│   │   ├── models/                   # [Dev B] SQLAlchemy 2.0 ORM models (models/__init__.py Integrator)
│   │   ├── schemas/                  # Pydantic v2 schemas (Dev A / Dev B / schemas/__init__.py Integrator)
│   │   ├── services/
│   │   │   ├── llm_service.py        # [Dev A] Gemini 3.5/2.5 Flash Lite + Ollama + 429 Cost-Guard
│   │   │   ├── rag_service.py        # [Dev A] Workspace-isolated RAG orchestrator
│   │   │   ├── ticket_copilot_service.py # [Dev A] AI triage & draft reply structured output
│   │   │   ├── verification_service.py # [Dev A] 3-stage Synthetic QA -> Self-Test -> AI Judge
│   │   │   ├── agent_tools.py        # [Dev A] Tool registry & execution hook for Agentic workflows
│   │   │   ├── ticket_service.py     # [Dev B] Database ticket CRUD, SLA calculation, filtering
│   │   │   ├── document_service.py   # [Dev B] PDF/TXT/MD text extraction & recursive chunker
│   │   │   ├── embedding_service.py  # [Dev B] Vector embeddings + PostgreSQL pgvector search
│   │   │   ├── fallback_service.py   # [Dev B] Pure-Python Okapi BM25 deterministic matcher
│   │   │   └── ai_usage_logger.py    # [Dev B] Background async AI telemetry logger
│   │   └── main.py                   # [Integrator] FastAPI ASGI app factory, CORS, timing middleware
│   ├── data/
│   │   ├── prompts.json              # [Dev A] Externalized, versioned system prompt catalog
│   │   ├── seed_faq.json             # [Dev A] Curated 12-item FAQ dataset for BM25 fallback
│   │   ├── eval_dataset.json         # [Dev A] 24-case AI benchmark evaluation dataset
│   │   └── sample_documents/         # [Dev A] Domain sample docs (SmileCare, TechStore)
│   ├── scripts/                      # CLI utilities (run_eval.py [Dev A], reembed_chunks.py [Dev B])
│   └── tests/                        # Per-module automated Pytest suites
│       ├── test_rag_module.py        # [Dev A] RAG, prompt loader & agent tools module tests
│       ├── test_ollama_provider.py   # [Dev A] Dual AI provider unit tests
│       ├── ai/                       # [Dev A] AI structured output & agent tool tests
│       ├── test_tickets_module.py    # [Dev B] Ticket SLA, categories & triage module tests
│       ├── test_auth_module.py       # [Dev B] Security guardrails & auth tests
│       ├── test_workspace_and_verification.py # [Dev B] Workspaces & verification pipeline
│       ├── platform/                 # [Dev B] Platform, pgvector & DB migration tests
│       ├── test_api.py               # [Dev C] Core API integration tests
│       ├── common/                   # [Dev C] Cross-feature scenario tests
│       └── conftest.py               # [Integrator] Pytest fixtures & dependency overrides
├── frontend/                         # React 19 + Vite 6 + Tailwind CSS v4 SPA
│   ├── src/
│   │   ├── components/               # [Dev C] Core screen components
│   │   ├── features/                 # [Dev C] Isolated feature subfolders (auth, telemetry, tools)
│   │   ├── services/
│   │   │   ├── api/                  # [Dev C] Modular API client methods (auth, chat, tickets, etc.)
│   │   │   ├── mocks/                # [Dev C] Offline mock fixtures
│   │   │   ├── api.ts                # [Integrator] Central API facade
│   │   │   └── api/client.ts         # [Integrator] Shared fetch client
│   │   ├── data.ts                   # [Dev C] Local fallback mock dataset
│   │   ├── types/                    # [Integrator] Modular TypeScript interfaces
│   │   ├── types.ts                  # [Integrator] Canonical TypeScript interfaces facade
│   │   └── App.tsx                   # [Dev C] Root tab & state coordinator
│   ├── Dockerfile                    # [Integrator] Multi-stage production container Dockerfile
│   ├── nginx.conf                    # [Integrator] Nginx reverse proxy configuration
│   ├── package.json                  # [Integrator]
│   └── vite.config.ts                # [Integrator]
├── docs/                             # Governing specifications, ADRs, audit & plan
│   ├── adr/                          # [Integrator] ADR-001 .. ADR-004
│   ├── audit/                        # [Integrator] 00-checklist, 01-gap-analysis, etc.
│   ├── plan/                         # [Integrator] PLAN.md, WORKSTREAMS.md, GIT_WORKFLOW.md, PROMPTS_FOR_DEVS.md
│   ├── spec/                         # [Integrator] CONTRACTS.md, SPEC.md
│   ├── ARCHITECTURE.md               # [Integrator] This file
│   ├── API_CONTRACT.md               # [Integrator] Frozen REST API schemas
│   ├── DESIGN.md                     # [Integrator] UI/UX tokens & 4-state specifications
│   ├── DEV_START_HERE.md             # [Integrator] Mandatory developer onboarding guide
│   ├── PROPOSAL.md                   # [Dev C] 12 User Stories & Requirement Traceability Matrix
│   ├── REPORT.md                     # [Dev C] Formal capstone project report
│   ├── PRESENTATION_AND_DEMO.md      # [Dev C] 15-slide deck & demo playbook
│   └── TEST_ACCEPTANCE.md            # [Dev C] Acceptance test matrix
├── scripts/                          # Windows batch launchers & python governance tools
│   ├── check_ownership.py            # [Integrator] Pre-commit ownership validation tool
│   ├── gen_codeowners.py             # [Integrator] CODEOWNERS generation script
│   ├── ownership_map.py              # [Integrator] Single source of truth ownership map
│   ├── verify_setup.ps1              # [Integrator] Universal 9-gate environment verifier
│   └── *.bat                         # [Integrator] Batch launchers
├── AI_USAGE.md                       # [Integrator] AI usage disclosure & failure/fix case studies
├── AGENTS.md                         # [Integrator] Master rules for AI assistants & developers
└── docker-compose.yml                # [Dev B] PostgreSQL 16 (pgvector) + Backend + Frontend orchestration
```

---

## 2. Module Ownership Matrix (Team of 3 Members)

To prevent merge conflicts during parallel development, every file in the repository belongs to exactly ONE designated owner. The team consists of **exactly 3 members**:
- **Dev A (Owner 1):** AI Engine & Evaluation (`@TheOrijinnn`)
- **Dev B (Owner 2) & Integrator:** Platform, Data & Security + Integrator Hat (`@BapVitHoang`)
- **Dev C (Owner 3):** Frontend UX, QA & Capstone Documentation (`@TKhanh`)

| Developer / Role | Owned Backend Modules | Owned Frontend, Infra & Docs | Dedicated Test Suites |
| :--- | :--- | :--- | :--- |
| **Dev A (Owner 1: AI Engine)** | `services/llm_service.py`, `rag_service.py`, `ticket_copilot_service.py`, `verification_service.py`, `agent_tools.py`, `core/prompts.py`, `endpoints/chat.py`, `chat_stream.py`, `chat_actions.py`, `endpoints/ai_usage.py`, `knowledge.py`, `schemas/ai_structured.py`, `schemas/chat.py`, `schemas/verification.py`, `backend/data/*`, `backend/scripts/run_eval.py`, `export_finetune_dataset.py`, `Modelfile` | `docs/notes/A.md`, `docs/notes/A-ai-usage.md`, `docs/notes/A-eval-report.md`, `docs/requests/devA.md` | `backend/tests/test_rag_module.py`, `test_ollama_provider.py`, `backend/tests/ai/*` |
| **Dev B (Owner 2: Platform & Security)** | `backend/Dockerfile`, `services/ticket_service.py`, `document_service.py`, `embedding_service.py`, `fallback_service.py`, `ai_usage_logger.py`, `core/deps.py`, `core/security.py`, `db/base.py`, `session.py`, `seed/*`, `models/*`, `schemas/ticket.py`, `workspace.py`, `document.py`, `health.py`, `knowledge.py`, `auth.py`, `endpoints/tickets.py`, `agent.py`, `workspaces.py`, `documents.py`, `auth.py`, `health.py`, `scripts/reembed_chunks.py` | `docker-compose.yml`, `docs/notes/B.md`, `docs/notes/B-ai-usage.md`, `docs/requests/devB.md` | `backend/tests/test_tickets_module.py`, `test_auth_module.py`, `test_workspace_and_verification.py`, `backend/tests/platform/*` |
| **Dev C (Owner 3: Frontend UX & Docs)** | `backend/PYTHON_FILES_EXPLANATION.md` | `frontend/src/*` (components, features, services/api, services/mocks, data.ts, App.tsx, main.tsx, index.css, metadata.json), `README.md`, `docs/PROPOSAL.md`, `docs/TEST_ACCEPTANCE.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/notes/C.md`, `docs/notes/C-ai-usage.md`, `docs/requests/devC.md` | `backend/tests/test_api.py`, `backend/tests/common/*` |
| **Integrator Hat (Hoang / Dev B)** | `api/v1/api.py`, `core/config.py`, `core/exceptions.py`, `schemas/__init__.py`, `services/__init__.py`, `models/__init__.py`, `requirements.txt`, `.env.example`, `conftest.py`, `pytest.ini`, `backend/README.md` | `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/package*.json`, `tsconfig.json`, `vite.config.ts`, `types.ts`, `types/*`, `services/api.ts`, `services/api/index.ts`, `services/api/client.ts`, `AI_USAGE.md`, `docs/DESIGN.md`, `docs/DEV_START_HERE.md`, `docs/API_CONTRACT.md`, `docs/spec/CONTRACTS.md`, `docs/adr/*`, `docs/audit/*`, `docs/plan/*`, `docs/requests/template.md`, `AGENTS.md`, `.cursorrules`, `.gitattributes`, `.gitignore`, `.github/*`, `scripts/*` | All shared test fixtures |

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
