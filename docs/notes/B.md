# Developer B — Technical Notes & Decisions

> Workstream: Platform, Data & Security (`feature/b-platform`)  
> Owner: Developer B

## 1. Ongoing Implementation Notes

### Task B1: OAuth2 Authentication, HS256 JWT, and RBAC Implementation (`TASK-12` / `REQ-06`, `REQ-09`, `REQ-36`)
1. **Pydantic v2 Schemas (`backend/app/schemas/auth.py`):**
   - Implemented `OAuth2LoginRequest` supporting both Google ID Token (`credential`) and seeded Demo account (`email`).
   - Implemented `OAuth2PasswordRequest` for standard username/password grant.
   - Defined `TokenResponse` and `UserProfileResponse`.
2. **Real HS256 JWT Issuance & Verification:**
   - In `backend/app/api/v1/endpoints/auth.py`: Implemented `create_access_token` using PyJWT with expiration claims (`exp`, `iat`, `sub`, `role`, `user_id`, `workspace_id`).
   - In `backend/app/core/deps.py`: Updated `get_current_user` to decode and verify JWT tokens against `settings.JWT_SECRET_KEY` while retaining backward-compatibility for legacy demo tokens (`demo_jwt_token_for_{email}`).
3. **RBAC & Customer Data Isolation:**
   - In `backend/app/api/v1/endpoints/tickets.py`:
     - Regular customers (`role != "admin"`) only see their own tickets (`customer_email == current_user.email`).
     - Regular customers attempting to read another user's ticket details are rejected with `HTTP 403 Forbidden`.
     - `PATCH /tickets/{id}` and `DELETE /tickets/{id}` are strictly guarded by `require_role("admin")`.
   - In `backend/app/api/v1/endpoints/agent.py`:
     - Copilot draft regeneration (`/agent/tickets/{id}/generate-draft`) is strictly restricted to `admin` role.
4. **Automated Test Coverage:**
   - Extended `backend/tests/test_auth_module.py` with 6 dedicated test cases covering login, token resolution, 401 unauthorized handling, and RBAC data isolation. All 49 test cases pass (100%).

### Task B2: Server-Side Sorting, Pagination Count Header, Delete API & Copilot Integration (`TASK-13` / `REQ-15`, `REQ-30`, `REQ-31`)
1. **Single-Call Copilot Integration (`backend/app/services/ticket_service.py`):**
   - Connected `ticket_copilot_service.generate_ticket_triage_and_draft()` in `create_ticket()` and `generate_draft_reply()` to obtain structured classification, tag extraction, and localized Vietnamese draft replies.
2. **Server-Side Sorting & Pagination Header (`backend/app/api/v1/endpoints/tickets.py`):**
   - Added `sort_by` (`created_at`, `priority`, `status`, `sla_hours`) and `sort_order` (`asc`, `desc`) query parameters to `GET /api/v1/tickets`.
   - Added count calculation matching current user and filter criteria, returning total records via `X-Total-Count` response header.
3. **Delete Endpoints (`tickets.py` & `workspaces.py`):**
   - `DELETE /api/v1/tickets/{ticket_id}`: Admin-only deletion returning `HTTP 204 No Content`.
   - `DELETE /api/v1/workspaces/{id}`: Admin-only deletion returning `HTTP 204 No Content`. Explicitly guards default workspace (ID=1) with `HTTP 400 Bad Request`.
4. **Automated Test Coverage:**
   - Extended `backend/tests/test_tickets_module.py` with 3 test cases for sorting, `X-Total-Count` header, workspace deletion rules, and copilot triage integration. All 52 tests pass (100%).

### Task B3 & B4: Dual-Dialect pgvector, PII Redaction & Platform Verification (`TASK-14` / `REQ-07`, `REQ-11`, `REQ-28`, `REQ-38`)
1. **Dual-Dialect pgvector Mapping (`backend/app/models/knowledge.py`):**
   - Configured `Vector(768).with_variant(JSON(), "sqlite")` from `pgvector.sqlalchemy` for `KnowledgeChunk.embedding` and `FAQItem.embedding`.
2. **PostgreSQL Extension Initialization (`backend/app/db/session.py`):**
   - Added automatic execution of `CREATE EXTENSION IF NOT EXISTS vector` on engine startup when PostgreSQL is detected.
3. **PII Masking & Dual-Mode Vector Search (`backend/app/services/embedding_service.py`):**
   - Enforced `redact_pii(text)` sanitization before dispatching queries to external Google Gemini / Ollama Embedding APIs.
   - Enhanced `search_similar_chunks()`: If running on PostgreSQL, dispatches native SQL pgvector cosine distance query (`<=>` operator); if running on SQLite, falls back seamlessly to in-memory cosine similarity calculation.
4. **Platform Automated Test Suite (`backend/tests/platform/test_pgvector_and_db.py`):**
   - Added tests verifying dual-dialect mapping, PII masking, and SQLite fallback similarity.
5. **Docker Compose Verification:**
   - Validated `docker compose config` with `postgres: pgvector/pgvector:pg16`, `backend`, and `frontend`.
6. **AI Usage & Prompting Log (`docs/notes/B-ai-usage.md`):**
   - Documented all 3 sessions and real bug diagnostics.

---

## 2. Decision Log
- Date: 2026-10-20 — Configured dual-dialect `Vector(768).with_variant(JSON(), "sqlite")` in `models/knowledge.py` to ensure local tests pass without PostgreSQL.
- Date: 2026-10-21 — Implemented HS256 JWT token generation and role-based data isolation on ticket endpoints (`admin` vs `user`), ensuring customers cannot access cross-tenant or other users' support tickets.
- Date: 2026-10-21 — Added `X-Total-Count` header and server-side sorting to `GET /api/v1/tickets`, hooked up `ticket_copilot_service` into ticket creation, and guarded workspace deletion (`id=1` blocked).
- Date: 2026-10-21 — Enabled native pgvector SQL cosine search with SQLite in-memory fallback, and masked PII before calling external embedding APIs.
- Date: 2026-10-23 — Established `docs/TEAM_ROSTER.md` as the single source of truth for personal data with neutral defaults, purged unverified student data across `README.md`, `PROPOSAL.md`, and `REPORT.md`, added `scripts/check_roster.py` gate to `verify_setup.ps1` and CI, and purged recovered stash files containing fabricated data.

---

## 3. Review Rounds (Self-Review Loop)

### Round 1 (2026-10-23)
- **Subagents Dispatched (4 in parallel):**
  1. Skeptical Verifier (`a311ce78...`)
  2. Requirements & Honesty Auditor (`6b77669b...`)
  3. Security & Robustness Reviewer (`ba7988c7...`)
  4. Ownership & Merge-Conflict Hunter (`25c98217...`)
- **Key Findings Identified:**
  - `FIND-01` / `FIND-OWN-01` (High): Potential 3-way content merge conflict in `docs/requests/devC.md` between `Hoang` (CR-002) and `feature/c-frontend-docs` (CR-001).
  - `SEC-ROB-01` (High): Decomposed Unicode NFD Vietnamese strings could bypass regex matching in `scripts/check_roster.py`.
  - `SEC-ROB-02` (High): Markdown bold/backtick formatting (`**Name** (Dev A)`) could break `name_role_match` in `scripts/check_roster.py`.
  - `SEC-ROB-04` (Medium): Unstripped markdown backticks in `TEAM_ROSTER.md` cells could cause verification false positives.
  - `AUDIT-02` (Medium): Font kerning / glyph splitting during PDF extraction in `pypdf` (`"Nguy ễ n Nh ậ t Huy"`) could evade text scanning.
  - `FIND-02` (Medium): Typo in `docs/audit/05-git-state-audit.md:194` referencing `passlib` instead of `google-auth`.
  - `FIND-03` (Medium): Ambiguity in `docs/audit/05-git-state-audit.md` §8.2 regarding status of extracted plain files.
  - `FIND-04` (Medium): Binary PDF and slide deliverables on `feature/c-frontend-docs` contained unverified student names and MSSVs.
  - `FIND-07` / `SEC-ROB-05` / `SEC-ROB-07` (Low): Missing `@TKhanh` handle mapping in `ownership_map.py` and `AGENTS.md:168`, narrow MSSV regex, and absolute path reporting.
- **Fixes Implemented:**
  - **Conflict Prevention:** Consolidated both CR-001 (Dev C ownership extensions) and CR-002 (action item for Dev C PDF/slides regeneration) in `docs/requests/devC.md`.
  - **Check Roster Hardening:** Added `unicodedata.normalize("NFC", ...)` across all inputs and roster entries, stripped markdown formatting from candidate lines and table cells, broadened MSSV regex to `\b(2[0-5]11\d{4})\b`, added intra-word kerning space collapse for PDF extraction, and used relative paths for missing file reporting.
  - **Documentation Harmonization:** Corrected `passlib` $\to$ `google-auth` in audit notes, clarified the subsequent purge of recovered files in commit `d080b82`, updated `AGENTS.md` and `scripts/ownership_map.py` to map Dev C to `@TKhanh`, and regenerated `.github/CODEOWNERS`.
- **Rejected Items:** None rejected without rationale. All valid findings were directly resolved and verified.
- **Stop Condition Evaluation:**
  - Zero unresolved Blocker or High findings.
  - All verification commands green (10/10 verification gate in `verify_setup.ps1`, 55/55 pytest tests passing, 0 TypeScript errors, clean Vite production build).
  - Stop early condition satisfied after Round 1.



---

## Plan (Prompt 2 - Dev B + Integrator)

Environment found in Task 0 (see Evidence): worktree smartdesk-B, no backend/.env (git-ignored; created from .env.example, no key), Docker Desktop daemon not running.

- **Task 1 (JWT secret):**
  files: core/config.py (Integrator), core/security.py, docker-compose.yml, backend/.env.example, tests/platform/test_jwt_secret.py.
  approach: stop storing the old default literal in code; keep only its SHA-256 to recognise it. A Settings `model_validator(after)` replaces an empty/known-default secret with `secrets.token_urlsafe(48)` when DEMO_LOGIN_ENABLED is true (so tests, which skip lifespan, are covered too) and leaves it unusable when demo is OFF so `validate_auth_configuration` still refuses to start. One startup warning without the secret. compose passes `JWT_SECRET_KEY: ${JWT_SECRET_KEY:-}`; .env.example has an empty value.
  proof: 3 offline tests + `git grep -n` for the old string (only test files).
  risk: several workers would each get a different secret (documented in the warning); tests that assume the old default.
- **Task 2 (dependency truth):** venv in %TEMP% outside the repo, `pip install -r`, import app, pytest; AST scan of imports vs requirements.txt. Remove only packages not imported anywhere and not required by kept packages; add missing ones. risk: local Python 3.13 differs from Docker python:3.11; google-generativeai may be a transitive requirement.
- **Task 3 (Docker/pgvector):** Docker daemon is down, so per Task 0 this is BLOCKED. Still delivered offline: scripts/smoke_docker.ps1 (syntax-checked with the PowerShell parser only, NOT run). Nothing about PostgreSQL is claimed as verified.
- **Task 4 (cooldown route):** agent.py gets `POST /agent/reset-cooldown` (admin only, same body as the existing route); the existing `/agent/ai-usage/reset-cooldown` in ai_usage.py (Dev A file, untouched) stays as alias; API_CONTRACT.md states both. backend/data/eval_runs/.gitignore with `*` and `!.gitignore`, proved by `git check-ignore -v`. proof: offline route test (admin 200, user 403, no token 401).
- **Task 5 (REQ-08):** grep frontend/package.json, frontend/src and a fresh `frontend/dist` (needs `npm ci` in this worktree); `git log -S "AIza"` printing subjects/file names only.
- **Task 6 (notes):** B.md / B-ai-usage.md by commit subject, section "Giải thích code" using names read from the code.
- Out-of-scope findings go to docs/requests/devB.md, one line each.

---

## Evidence

### Task 0 - setup check
- `git merge-base --is-ancestor origin/Hoang HEAD` returned exit 1 before and exit 0 after `git merge origin/Hoang` (merge commit "Merge remote-tracking branch 'origin/Hoang' into feature/b-platform").
- Identity: `git config user.name` = `Bap`, `git config user.email` = the roster email for the Dev B row. The roster row still has `verified_by_user = false`; the human confirmed in the chat that the full name is Ngô Việt Hoàng and the GitHub name is Bap, and confirmed that smartdesk-B is the worktree.
- `backend/.env` did not exist in this worktree (it is git-ignored, `git check-ignore -v backend/.env` -> `.gitignore:8:.env`). It was created from `backend/.env.example` (no key). GEMINI_API_KEY: **missing** in this worktree.
- `docker version` -> exit 1, `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` => Docker Desktop is not running => Task 3 is BLOCKED (see Task 3).
- `scripts/verify_setup.ps1` -> `RESULT: 7/10 CHECKS PASSED`. PASS: git, .env, backend deps, backend pytest (`66 passed in 5.44s`), docker-compose config, ownership, roster. FAIL: [4/10] `frontend/node_modules not found`, [6/10] lint and [7/10] build (both fail because node_modules is missing in this fresh worktree; not a code failure, re-run after `npm ci`).

### Task 1 - JWT secret
- `python -m pytest backend/tests/platform/test_jwt_secret.py -q` -> `13 passed in 1.97s`.
- Mutation check (to prove the tests test something): validator disabled -> `6 failed, 7 passed`; startup refusal removed -> `1 failed, 12 passed`; both files restored -> `13 passed in 1.92s`.
- `python -m pytest backend/tests -q` -> `79 passed in 6.14s`, exit 0.
- `git grep --untracked -n "<old default string>"` -> one hit, `backend/tests/platform/test_jwt_secret.py:22` (the test that proves rejection). `.env.example` now has `JWT_SECRET_KEY=""`, compose passes `JWT_SECRET_KEY: ${JWT_SECRET_KEY:-}`; `docker compose config -q` exit 0 (config parse only).

### Task 2 - Dependency truth (REQ-11)
- Clean virtual environment created in `$env:TEMP\sd-venv-clean` with `include-system-site-packages = false` (Python 3.13.7).
- Executed `pip install -q -r backend/requirements.txt` -> exit 0. Total packages in `pip freeze`: 67 (including transitive dependencies).
- Executed `pytest backend/tests -q -p no:cacheprovider` inside the clean venv -> `79 passed in 8.76s`, exit 0.
- Performed full AST scan of all import statements across `backend/app`, `backend/scripts`, and `backend/tests`:
  - `fastapi`, `uvicorn`: ASGI framework and server runner.
  - `pydantic`, `pydantic-settings`: Schemas and config management.
  - `email-validator`: Enforces RFC validation on `EmailStr` in auth and ticket schemas.
  - `sqlalchemy[asyncio]`, `greenlet`: Async ORM core and greenlet coroutine driver.
  - `aiosqlite`, `asyncpg`: Dual-driver support for SQLite and PostgreSQL.
  - `httpx`: Async HTTP client for Ollama and tests.
  - `google-genai`: Primary SDK for Gemini 3.5 Flash Lite.
  - `google-generativeai`: Backward-compatibility fallback SDK used in `llm_service.py:75` and `embedding_service.py:57`.
  - `pytest`, `pytest-asyncio`: Automated test suites.
  - `python-dotenv`: Environment variable loader for scripts and tests.
  - `pypdf`: Document ingestion engine in `document_service.py`.
  - `python-multipart`: Form-data parser for OAuth2 login endpoints.
  - `pyjwt`: HS256 JWT encoding, decoding, and claims verification.
  - `google-auth`: Signature verification for Google OAuth2 ID tokens.
  - `pgvector`: PostgreSQL vector type bindings for hybrid search.
- Outcome: Zero stale dependencies detected. No packages removed or added. All 20 entries in `backend/requirements.txt` are verified active and necessary.

### Task 3 - Docker & PostgreSQL + pgvector (REQ-07, REQ-11) — BLOCKED
- Status: **BLOCKED** due to Docker Desktop Linux Engine daemon not running on the host Windows machine.
- Command executed: `docker version` and `powershell -ExecutionPolicy Bypass -File scripts/smoke_docker.ps1`.
- Actual output:
  `ERROR: error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.47/info": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- Actions delivered offline (Integrator hat):
  - Created `scripts/smoke_docker.ps1` (Integrator-owned) automating `docker compose build`, `docker compose up -d`, healthcheck polling on `http://localhost:8000/api/v1/health`, Nginx reverse proxy test on `http://localhost:3000`, demo login authentication (`POST /auth/oauth2/login`), ticket listing (`GET /tickets` verifying `X-Total-Count`), and SQL check for PostgreSQL extension `vector`.
  - Validated syntax of `scripts/smoke_docker.ps1` using `[System.Management.Automation.Language.Parser]::ParseFile()` -> `SYNTAX_OK` (0 errors).
  - Validated graceful blocker detection: Running `smoke_docker.ps1` correctly detects Docker failure and exits with code 1 without corrupting local state.
  - Per Rule 3 & Rule 8 (No Fabrication, Stop Conditions): PostgreSQL live queries and live container execution are NOT claimed as verified because Docker is offline.

### Task 4 - Cooldown route & small frozen-file fixes (REQ-22, REQ-33)
- Implemented `POST /api/v1/agent/reset-cooldown` directly in `backend/app/api/v1/endpoints/agent.py` (Dev B owned), guarded by `require_role("admin")`, invoking `llm_service.reset_cooldown()` and returning `ResetCooldownResponse(status="success", message=..., cooldown_active=False)`.
- Updated `docs/API_CONTRACT.md` (Integrator hat) noting that `POST /api/v1/agent/reset-cooldown` is the primary endpoint and `POST /api/v1/agent/ai-usage/reset-cooldown` is maintained as an alias for telemetry convenience.
- Created `backend/data/eval_runs/.gitignore` with `*` and `!.gitignore`.
- Verified `.gitignore` pattern:
  - `git check-ignore -v backend/data/eval_runs/test_run.json` -> `backend/data/eval_runs/.gitignore:1:*` (ignored).
  - `git check-ignore -v backend/data/eval_runs/.gitignore` -> `backend/data/eval_runs/.gitignore:2:!.gitignore` (tracked).
- Registered `backend/data/eval_runs/.gitignore` and `scripts/smoke_docker.ps1` under `integrator` in `scripts/ownership_map.py` and updated `.github/CODEOWNERS`.
- Created offline platform test `backend/tests/platform/test_agent_reset_cooldown.py`:
  - `test_reset_cooldown_unauthenticated_rejected`: 401 Unauthorized.
  - `test_reset_cooldown_regular_user_forbidden`: 403 Forbidden.
  - `test_reset_cooldown_admin_success_and_clears_timer`: 200 OK and asserts `llm_service.is_in_cooldown() is False`.
  - `test_reset_cooldown_alias_backward_compatibility`: 200 OK.
  - Test command output: `4 passed in 0.82s`.
- Full pytest suite: `83 passed in 7.49s`.


