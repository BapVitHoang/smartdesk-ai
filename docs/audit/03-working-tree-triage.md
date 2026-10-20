# Phase 2 Cleanup: Working Tree Triage & Restructure Verification (`03-working-tree-triage.md`)

> **Date:** 2026-10-20  
> **Branch:** `Hoang` (ahead of `origin/Hoang` by 7 commits; safety backup branch created at `backup/pre-cleanup-20261020`)  
> **Baseline `HEAD` Commit:** `14445be` (`test(ci): isolate test database in conftest and add GitHub Actions CI workflow`)

---

## 1. Analysis of the 80 Uncommitted `git status` Entries

Running `git status` showed **80 entries** (`38` staged `new file:` entries + `42` unstaged entries consisting of `14` `modified:` and `28` `deleted:`).  
Running `git diff HEAD -M --name-status` (comparing the working tree + index against `HEAD` with rename detection enabled) proved that **all 28 deleted files are 1-to-1 renames (`R100` / `R083–R099`)** into `frontend/`, `docs/`, and `scripts/`, leaving **52 net logical file changes** (`28` renames, `14` modifications, `10` new files).

### Group A: Intentional Folder Restructure (28 File Moves = 56 `git status` Entries)
All 28 deleted root files have verified replacements at their new paths:

| Old Path (Deleted in Working Tree) | New Path (Staged in Index) | Similarity (`git diff HEAD -M`) | Verification Evidence |
| :--- | :--- | :---: | :--- |
| `.env.example` | `frontend/.env.example` | `R100` (100%) | Byte-for-byte identical move |
| `index.html` | `frontend/index.html` | `R100` (100%) | Byte-for-byte identical move |
| `metadata.json` | `frontend/metadata.json` | `R100` (100%) | Byte-for-byte identical move |
| `package.json` | `frontend/package.json` | `R100` (100%) | Byte-for-byte identical move |
| `package-lock.json` | `frontend/package-lock.json` | `R100` (100%) | Byte-for-byte identical move |
| `tsconfig.json` | `frontend/tsconfig.json` | `R100` (100%) | Byte-for-byte identical move |
| `vite.config.ts` | `frontend/vite.config.ts` | `R100` (100%) | Byte-for-byte identical move |
| `src/App.tsx` | `frontend/src/App.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/data.ts` | `frontend/src/data.ts` | `R100` (100%) | Byte-for-byte identical move |
| `src/index.css` | `frontend/src/index.css` | `R100` (100%) | Byte-for-byte identical move |
| `src/main.tsx` | `frontend/src/main.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/types.ts` | `frontend/src/types.ts` | `R100` (100%) | Byte-for-byte identical move |
| `src/services/api.ts` | `frontend/src/services/api.ts` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/AgentDashboardView.tsx` | `frontend/src/components/AgentDashboardView.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/ChatView.tsx` | `frontend/src/components/ChatView.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/Footer.tsx` | `frontend/src/components/Footer.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/Header.tsx` | `frontend/src/components/Header.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/KnowledgeManagerView.tsx` | `frontend/src/components/KnowledgeManagerView.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `src/components/TicketFormView.tsx` | `frontend/src/components/TicketFormView.tsx` | `R100` (100%) | Byte-for-byte identical move |
| `API_CONTRACT.md` | `docs/API_CONTRACT.md` | `R100` (100%) | Byte-for-byte identical move |
| `DESIGN.md` | `docs/DESIGN.md` | `R100` (100%) | Byte-for-byte identical move |
| `PROPOSAL.md` | `docs/PROPOSAL.md` | `R100` (100%) | Byte-for-byte identical move |
| `TEST_ACCEPTANCE.md` | `docs/TEST_ACCEPTANCE.md` | `R100` (100%) | Byte-for-byte identical move |
| `implementation_plan_smartdesk_ai_upgrade.md` | `docs/implementation_plan_smartdesk_ai_upgrade.md` | `R099` (99%) | Moved to `docs/`; updated `API_CONTRACT.md` link on line 88 |
| `install.bat` | `scripts/install.bat` | `R095` (95%) | Moved to `scripts/`; added `cd /d "%~dp0.."` and `--prefix frontend` |
| `start.bat` | `scripts/start.bat` | `R097` (97%) | Moved to `scripts/`; updated `cd /d "%~dp0..\frontend"` |
| `start_all.bat` | `scripts/start_all.bat` | `R083` (83%) | Moved to `scripts/`; updated `scripts\start_backend.bat` and `..\frontend` |
| `start_backend.bat` | `scripts/start.bat` $\to$ `scripts/start_backend.bat` | `R097` (97%) | Moved to `scripts/`; updated `cd /d "%~dp0..\backend"` |

### Group B: Documentation, AI Rules & Audit Deliverables (13 Files)
1. **Modified AI Rule & Doc Files (7 files):**
   - `.agents/rules/backend-standards.md` — Updated `API_CONTRACT.md` reference to `docs/API_CONTRACT.md`.
   - `.agents/rules/frontend-standards.md` — Updated `src/*` paths to `frontend/src/*` and `DESIGN.md` to `docs/DESIGN.md`.
   - `.agents/skills/qa-acceptance-tester/SKILL.md` — Updated `TEST_ACCEPTANCE.md` link and added `--prefix frontend` to npm commands.
   - `.agents/skills/react-frontend-builder/SKILL.md` — Updated `src/*` to `frontend/src/*`, `DESIGN.md` to `docs/DESIGN.md`, and added `--prefix frontend`.
   - `.cursorrules` — Updated paths (`docs/*`, `frontend/src/*`, `--prefix frontend`).
   - `AGENTS.md` — Updated document links to `./docs/*`, frontend paths to `frontend/src/*`, and script paths to `scripts/*.bat`.
   - `README.md` — Added `scripts/` and `docs/` sections to the directory tree.
2. **Staged Audit, Plan & Spec Deliverables (5 files):**
   - `docs/audit/00-checklist.md`, `docs/audit/01-gap-analysis.md`, `docs/audit/02-brainstorm-notes.md`, `docs/plan/PLAN.md`, `docs/spec/SPEC.md`.
3. **CI Workflow Update (1 file):**
   - `.github/workflows/ci.yml` — Added `working-directory: frontend` and `cache-dependency-path: frontend/package-lock.json` for the restructured `frontend/` folder.

### Group C: Real Code & Local Ollama Provider Changes (11 Files)
1. **Modified Backend Files (6 files):**
   - `backend/app/core/config.py` — Added `AI_PROVIDER` (`"gemini"` | `"ollama"`), `OLLAMA_BASE_URL`, `OLLAMA_LLM_MODEL` (`"qwen2.5:3b"`), `OLLAMA_EMBEDDING_MODEL` (`"nomic-embed-text"`), `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_KEEP_ALIVE`.
   - `backend/.env.example` — Added corresponding `AI_PROVIDER` and `OLLAMA_*` example variables.
   - `backend/app/services/llm_service.py` — Added `_execute_ollama_call()` and provider routing between Gemini and Ollama.
   - `backend/app/services/embedding_service.py` — Added `_execute_ollama_embedding()` (`/api/embed`) and batch Ollama embedding support.
   - `backend/app/services/verification_service.py` — Updated availability checks from `not llm_service._client` to `not llm_service.is_available()`.
   - `backend/app/api/v1/endpoints/health.py` — Updated `/api/v1/health/smoke-test` to report active model (`ollama:qwen2.5:3b` vs `gemini-3.5-flash-lite`).
2. **New Backend / Ollama Utility & Test Files (5 files):**
   - `Modelfile` — Ollama model definition based on `qwen2.5:3b` with temperature `0.2` and Vietnamese customer support system prompt.
   - `backend/data/finetune_alpaca.jsonl` — 121-line fine-tuning dataset in Alpaca JSONL format.
   - `backend/scripts/export_finetune_dataset.py` — Script exporting `FAQItem` and `Ticket` records to JSONL.
   - `backend/scripts/reembed_chunks.py` — Script re-embedding `KnowledgeChunk` and `FAQItem` rows with the active provider.
   - `backend/tests/test_ollama_provider.py` — 7 unit tests verifying Ollama LLM and Embedding service methods.

### Group D: Generated / Junk Files in Working Tree (Must NOT Be Committed)
Verified via `git status --ignored -s`:
- `./smartdesk.db` — Stray SQLite file in the repository root left over from before commit `ea52761` anchored SQLite to `backend/smartdesk.db`. **Action:** Deleted stray root `./smartdesk.db` (keeping `backend/smartdesk.db` gitignored).
- `backend/.env` — Local environment file containing `GEMINI_API_KEY`. Properly ignored by `.gitignore`; verified `0` occurrences in staged/tracked files. Also updated `LLM_TIMEOUT_SECONDS=5.0` $\to$ `4.0` in local `backend/.env` to match `AGENTS.md` §4.1.
- `frontend/dist/`, `frontend/node_modules/`, `.pytest_cache/`, `backend/.pytest_cache/`, `backend/**/__pycache__/` — Properly gitignored.

### Group E: Suspicious Diffs, Deleted File Check & Line Endings
- **Deleted Files Without Replacement:** **0 files.** Every deleted file in `git status` is accounted for in Group A above.
- **Line Endings Check:** Comparing `git diff HEAD --stat` (`1587 insertions, 91 deletions`) vs `git diff HEAD -w --stat` (`1581 insertions, 85 deletions`) confirms there are no mass line-ending-only diffs (only 6 lines differed by trailing CR across 52 files). Added `.gitattributes` to enforce consistent line endings (`* text=auto`, `*.bat text eol=crlf`, source/docs `eol=lf`).

---

## 2. Step 2 Verification & Restructure Breakage Repairs

### 2.1 Verification Before Repairs
1. **Frontend Type Check (`npm run lint --prefix frontend`):** `PASS` (exit code `0`).
2. **Frontend Production Build (`npm run build --prefix frontend`):** `PASS` (`1681 modules transformed`, `dist/index.html` 1.53 kB, `dist/assets/index-DCAu2Fmc.js` 370.95 kB in `10.07s`).
3. **Backend Automated Test Suite (`$env:GEMINI_API_KEY=""; pytest backend/tests/ -v`):** `PASS` (`24 passed in 28.63s`).
4. **Docker Compose Validation (`docker compose config --quiet`):** `PASS` (exit code `0`, emitted warning: `the attribute version is obsolete`).
5. **Live Gemini API Model Verification:**
   - Executed `client.models.get(model=...)` against live Google GenAI API:
     - `models/gemini-1.5-flash` $\to$ `404 NOT_FOUND` (retired)
     - `models/text-embedding-004` $\to$ `404 NOT_FOUND` (retired)
     - `models/gemini-3.5-flash-lite` $\to$ `EXISTS`
     - `models/gemini-2.5-flash-lite` $\to$ `EXISTS`
     - `models/gemini-embedding-001` $\to$ `EXISTS`

### 2.2 Breakages & Inconsistencies Repaired
1. **Stale Root Paths in `README.md`, `docs/DESIGN.md`, `docs/implementation_plan_smartdesk_ai_upgrade.md`, and `scripts/install.bat`:**
   - Updated `README.md#L32` (`src/` $\to$ `frontend/src/`), `docs/DESIGN.md#L167` (`src/` $\to$ `frontend/src/`), `scripts/install.bat#L39` (`start_all.bat` $\to$ `scripts\start_all.bat`), and `docs/implementation_plan_smartdesk_ai_upgrade.md` path references.
2. **Working-Directory Dependent Paths in `backend/app/db/session.py` & `backend/scripts/*.py`:**
   - In `backend/app/db/session.py#L250-L253`, replaced `Path("backend/data") / rel_path` with `BACKEND_DIR / "data" / rel_path` so sample document seeding works regardless of the current working directory.
   - In `backend/scripts/export_finetune_dataset.py` and `backend/scripts/reembed_chunks.py`, imported `app.db.session as db_session` (`async with db_session.async_session_factory() as session:`) so that if `init_db()` falls back from PostgreSQL to SQLite and reassigns `async_session_factory`, the scripts use the live reassigned factory instead of a stale reference.
3. **CI Branch Triggers (`.github/workflows/ci.yml`) & `docker-compose.yml`:**
   - Added `"master"` and `"Hoang"` to `.github/workflows/ci.yml` push/PR branch triggers.
   - Removed obsolete `version: '3.8'` from `docker-compose.yml` so `docker compose config` runs with zero warnings.
4. **Frontend `package.json` & `metadata.json` Cleanup:**
   - Fixed Windows-incompatible `"clean": "rm -rf dist server.js"` script in `frontend/package.json`, removed unused server/LLM dependencies (`@google/genai`, `express`, `@types/express`, `dotenv`) from `frontend/package.json`, and fixed UTF-8 mojibake in `frontend/metadata.json`.


---

## 3. Step 3 Governing Document Corrections & Mandatory Deliverables Created

| Document | Contradiction / Issue Found | Fix Applied |
| :--- | :--- | :--- |
| [`AGENTS.md`](../../AGENTS.md) & [`.cursorrules`](../../.cursorrules) | Missing multi-developer module ownership boundaries, shared-file freeze policy, commit conventions, and explicit canonical SLA/category rules. | Added Section 6 (Multi-Agent & Team Collaboration Rules: Owner 1/2/3 boundaries, frozen shared files, Conventional Commits, branch naming, pre-commit test gate), canonical SLA (`2/4/8/24h`), and model fallback chain (`gemini-3.5-flash-lite` $\to$ `gemini-2.5-flash-lite` $\to$ `qwen2.5:3b` $\to$ BM25). |
| [`.agents/rules/*`](../../.agents/rules/) & [`.agents/skills/*`](../../.agents/skills/) | `.agents/skills/fastapi-backend-builder/SKILL.md#L6` referenced retired `Gemini 1.5 Flash`; `references/api_specs.md#L3` referenced `Next.js frontend according to DESIGN.md` and `Technical Bug` only. | Updated to `Gemini 3.5 Flash Lite / Ollama`, `React 19 + Vite 6 SPA`, `docs/DESIGN.md`, and canonical categories (`Bug Report` + `Technical Bug` alias). |
| [`docs/API_CONTRACT.md`](../API_CONTRACT.md) | Used `"Technical Bug"` while frontend used `"Bug Report"`; lacked a consolidated section for canonical enums, SLA hours, and RFC 7807 error codes. | Added Section 0 freezing canonical categories (`Bug Report` with `Technical Bug` alias), SLA hours (`2/4/8/24h`), status mapping, and RFC 7807 error format. |
| [`docs/PROPOSAL.md`](../PROPOSAL.md) | Claimed `Next.js 14 (SSR)`, `Redis Cache`, `WebSocket Server`, and `Vercel + Render`; only had 3 user stories; lacked a Requirement Traceability Matrix. | Updated architecture diagram and tech stack to match actual `React 19 + Vite 6 + FastAPI + pgvector/SQLite + Dual Provider`; expanded to 12 User Stories (`US-01..US-12`); added Section 4 Requirement Traceability Matrix. |
| [`docs/DESIGN.md`](../DESIGN.md) & [`README.md`](../../README.md) | Referenced pre-restructure `src/` instead of `frontend/src/` and non-existent `AI_REVIEW_LOG.md`. | Updated directory trees to `frontend/src/`, added Screen 4 (`KnowledgeManagerView.tsx`), and linked to `AI_USAGE.md` and `docs/ARCHITECTURE.md`. |
| [`docs/TEST_ACCEPTANCE.md`](../TEST_ACCEPTANCE.md) | Lines `155–221` were a copy-paste duplicate of Scenarios 1–4. | Removed duplicate section and updated automated test table (31 tests across 6 test files). |
| [`AI_USAGE.md`](../../AI_USAGE.md) & [`docs/adr/ADR-001..004.md`](../adr/) | Mandatory grading deliverables (`REQ-26`, `REQ-28`, `CRIT-09`) were missing. | Created `AI_USAGE.md` (with 3 real repo failure/fix case studies and Phase B/C `TODO` markers) and 4 ADRs (`ADR-001` through `ADR-004`). |

---

## 4. Step 4 Shared Foundation & Extension Points Verification

1. **Architecture & Ownership Document:** Created [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) defining exact file ownership for Owner 1 (AI/RAG), Owner 2 (Platform/Auth/Tickets), Owner 3 (Frontend/DevOps/QA), and the Integration Owner.
2. **Frozen Contracts:**
   - Aligned `calculate_sla_hours` in `backend/app/services/ticket_service.py` to `Urgent=2, High=4, Medium=8, Low=24`.
   - Added `BUG_REPORT = "Bug Report"` alongside `TECHNICAL_BUG = "Technical Bug"` in `backend/app/schemas/ticket.py`.
   - Added secondary cloud model fallback (`LLM_FALLBACK_MODEL_NAME="gemini-2.5-flash-lite"`) in `backend/app/core/config.py` and `backend/app/services/llm_service.py`.
3. **Conflict-Free Extension Points:**
   - Externalized prompt catalog: `backend/data/prompts.json` + `backend/app/core/prompts.py`.
   - Agent tool registry skeleton: `backend/app/services/agent_tools.py`.
   - Optional router auto-discovery in `backend/app/api/v1/api.py`.
   - Frontend feature extension directory: `frontend/src/features/README.md`.
   - Per-module test suites: `backend/tests/test_rag_module.py`, `backend/tests/test_tickets_module.py`, `backend/tests/test_auth_module.py`.
4. **Post-Repair Full Verification Output:**
   - `npm run lint --prefix frontend`: **PASS (0 errors)**
   - `npm run build --prefix frontend`: **PASS (`dist/` built in 2.30s)**
   - `docker compose config --quiet`: **PASS (0 warnings, 0 errors)**
   - `$env:GEMINI_API_KEY=""; pytest backend/tests/ -v`: **PASS (`31 passed in 26.21s`)**
