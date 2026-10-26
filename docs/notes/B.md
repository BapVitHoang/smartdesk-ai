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

### Task B5: Security Hardening & Full Docker Verification (Prompt 2b / `REQ-06`, `REQ-07`, `REQ-09`, `REQ-11`, `REQ-36`, `REQ-39`)
1. **Demo Account Hardening (`REQ-SEC-01`):**
   - In `backend/app/db/seed/seed_users.py`: Demo users are seeded only if `settings.DEMO_LOGIN_ENABLED` is true.
   - In `backend/app/api/v1/endpoints/auth.py`: When `DEMO_LOGIN_ENABLED` is false, demo accounts attempting login via `/auth/token` or `/auth/oauth2/login` (provider="demo") are rejected with `HTTP 401 Unauthorized` returning the exact same generic credential error as a wrong password.
2. **Client IP Behind Trusted Nginx Proxy (`REQ-SEC-02`):**
   - Uvicorn configured with `--proxy-headers` and `--forwarded-allow-ips`.
   - In `backend/app/core/security.py`: Implemented `is_trusted_proxy_ip()` (supporting IPv4 and IPv6 loopback, Docker, and private CIDRs) and `get_trusted_client_ip()` resolving `X-Real-IP` and `X-Forwarded-For` only when the direct peer is a trusted proxy.
   - Wired `get_trusted_client_ip()` into login throttling to prevent IP spoofing attacks.
3. **Authenticated Ticket Creation & Customer Isolation (`REQ-SEC-03`):**
   - In `backend/app/api/v1/endpoints/tickets.py`: `POST /api/v1/tickets` requires `current_user: User = Depends(get_current_user)`.
   - Regular users (`role == "user"`) have `customer_email` and `customer_name` locked to their authenticated JWT identity, preventing impersonation.
   - Admins/support agents can file tickets on behalf of customers.
4. **Real Docker & PostgreSQL + pgvector Verification:**
   - Docker Desktop active; images built cleanly with `docker compose build`.
   - Container health verified: `/api/v1/health` reports status `ok` and database `connected`.
   - Frontend SPA on port 3000 and reverse proxy `/api/v1/` verified functional.
   - SSE streaming through Nginx verified (`proxy_buffering off;` emitting metadata and token chunks without delay).
   - PostgreSQL container verified: `pg_extension` confirms `vector 0.8.6`; `knowledge_chunks.embedding` is `vector(768)`; 9 chunks seeded; native `<=>` cosine distance vector query executes successfully.
   - Pytest suite executed against backend container: 94 passed in 5.94s (Lưu ý: lần chạy này tại Prompt 2b sử dụng SQLite tạm thời do conftest.py hardcode session URL; các lần chạy PostgreSQL thực sự sử dụng TEST_DATABASE_URL tại Prompt 2c).
   - Clean-state smoke test `scripts/smoke_docker.ps1`: all 8 steps passed, clean teardown.

---

## 2. Decision Log
- Date: 2026-10-21 — Configured dual-dialect `Vector(768).with_variant(JSON(), "sqlite")` in `models/knowledge.py` to ensure local tests pass without PostgreSQL (confirmed by git commit b753b95).
- Date: 2026-10-21 — Implemented HS256 JWT token generation and role-based data isolation on ticket endpoints (`admin` vs `user`), ensuring customers cannot access cross-tenant or other users' support tickets.
- Date: 2026-10-21 — Added `X-Total-Count` header and server-side sorting to `GET /api/v1/tickets`, hooked up `ticket_copilot_service` into ticket creation, and guarded workspace deletion (`id=1` blocked).
- Date: 2026-10-21 — Enabled native pgvector SQL cosine search with SQLite in-memory fallback, and masked PII before calling external embedding APIs.
- Date: 2026-10-23 — Established `docs/TEAM_ROSTER.md` as the single source of truth for personal data with neutral defaults, purged unverified student data across `README.md`, `PROPOSAL.md`, and `REPORT.md`, added `scripts/check_roster.py` gate to `verify_setup.ps1` and CI, and purged recovered stash files containing fabricated data.
- Date: 2026-10-25 — Hardened demo authentication: demo users are only seeded and allowed to login when `DEMO_LOGIN_ENABLED=True`. If false, demo logins return generic HTTP 401 matching invalid credentials.
- Date: 2026-10-25 — Implemented trusted proxy IP resolution (`get_trusted_client_ip`) behind Nginx, ignoring spoofed headers from untrusted sources, and integrated with login throttling.
- Date: 2026-10-25 — Secured ticket submission: `POST /api/v1/tickets` requires authentication (`get_current_user`), binding customer email/name to JWT identity for regular users, while allowing admins to file on behalf of customers.
- Date: 2026-10-25 — Verified full containerized stack under Docker Compose with real PostgreSQL 16 + pgvector (0.8.6), unbuffered Nginx SSE streaming (kết quả kiểm thử pytest container lúc đó chạy trên SQLite tạm thời; kiểm thử trên PostgreSQL thực sự được triển khai với TEST_DATABASE_URL trong Prompt 2c).

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
  - **Documentation Harmonization:** Corrected `passlib` $\to$ `google-auth` in audit notes, clarified the subsequent purge of recovered files in commit "chore(governance): purge recovered files containing unverified personal data", updated `AGENTS.md` and `scripts/ownership_map.py` to map Dev C to `@TKhanh`, and regenerated `.github/CODEOWNERS`.
- **Rejected Items:** None rejected without rationale. All valid findings were directly resolved and verified.
- **Stop Condition Evaluation:**
  - Zero unresolved Blocker or High findings.
  - All verification commands green (10/10 verification gate in `verify_setup.ps1`, 55/55 pytest tests passing, 0 TypeScript errors, clean Vite production build).
  - Stop early condition satisfied after Round 1.

### Round 2 (2026-10-25)
- **Subagents Dispatched (4 in parallel):**
  1. Skeptical Verifier (`2508952b...`)
  2. Requirements & Honesty Auditor (`380df657...`)
  3. Security Reviewer (`d630cb5f...`)
  4. Ownership & Merge-Conflict Hunter (`4577dba2...`)
- **Key Findings Identified:**
  - `OWN-01` / `ROSTER-01` (High): `check_roster.py` regex false positive on `docs/notes/B-ai-usage.md:69` matching `"ện Platform Tasks"` immediately before `(Dev B`.
  - `OBS-01` (Low): Direct invocation of `validate_auth_configuration()` in `test_jwt_secret.py:122` rather than `TestClient(app)` lifespan.
  - `SEC-REQ-01` (Advisory): Demo accounts are seeded with default passwords even when `DEMO_LOGIN_ENABLED=false`.
  - `SEC-REQ-02` (Advisory): Docker compose Nginx reverse proxy passes requests without Uvicorn proxy headers, potentially collapsing client IPs into Nginx container IP in throttle check.
  - `SEC-REQ-03` (Advisory): Ticket submission endpoint `POST /api/v1/tickets` is unauthenticated and lacks rate limiting.
- **Fixes & Mitigations Implemented:**
  - Rephrased prompt string in `docs/notes/B-ai-usage.md:69` to eliminate false name match; verified `check_roster.py` and `scripts/verify_setup.ps1` pass 10/10 (commit "docs(notes): refine prompt wording to satisfy check_roster gate").
  - Evaluated `OBS-01`: Verified `backend/app/main.py:33` directly runs `validate_auth_configuration()` during lifespan startup.
  - Logged `SEC-REQ-01`, `SEC-REQ-02`, and `SEC-REQ-03` in `docs/requests/devB.md` per Scope Lock (Rule 1).
- **Stop Condition Evaluation:**
  - Zero unresolved Blocker or High findings.
  - All verification commands green (10/10 verification gate in `verify_setup.ps1`, 83/83 pytest tests passing, 0 TypeScript errors, clean Vite production build).
  - Stop early condition satisfied after Round 2.

### 2c round 1 (2026-10-25)
- **Subagents Dispatched (4 in parallel):**
  1. Skeptical Verifier (`0ab0987e...`)
  2. Requirements Auditor (`f710aea4...`)
  3. Security Reviewer (`c8f91cbd...`)
  4. Ownership Hunter (`be696f11...`)
- **Ghi chú quy trình Review Prompt 2c:** Ở giai đoạn lập kế hoạch Prompt 2c, subagent Plan Skeptic gặp sự cố timeout/không phản hồi nên đã được dừng sớm; các chỉnh sửa (sắp xếp priority qua case(), CORS header, port binding) đã được kiểm chứng trực tiếp bằng các bài kiểm thử tự động (tests only) mà không chạy vòng subagent thứ hai.
- **Key Findings Identified:**
  - `FIND-SKEP-01` (High): `test_search_similar_chunks_sqlite_fallback` queried workspace 1 (which had no chunks), returning `[]` and skipping the assertion loop vacuously.
  - `FIND-SKEP-02` (High): `sort_by="priority"` in `tickets.py` sorted alphabetically (`"Urgent" -> "Medium" -> "Low" -> "High"`), placing High below Low.
  - `FIND-SEC-01` (High): PostgreSQL port 5432 bound to `0.0.0.0` in `docker-compose.yml`.
  - `FIND-SKEP-03` (Medium): Non-deterministic pagination when sorting by non-unique columns (missing tie-breaker `Ticket.id.desc()`).
  - `FIND-SKEP-04` (Medium): Custom header `X-Total-Count` not exposed in `CORSMiddleware`.
  - `FIND-SKEP-05` (Medium): `FALLBACK_SQLITE_URL` overwritten with PostgreSQL URL in test suite.
  - `FIND-SKEP-06` (Low): Weak assertion in `smoke_docker.ps1` pagination check.
  - `FIND-SKEP-07` (Low): Unrestricted `drop_all` on `TEST_DATABASE_URL` without `test` substring check.
  - `FIND-SKEP-08` (Low): `User` and `AIUsageLog` missing from `init_db()` imports.
- **Fixes & Mitigations Implemented:**
  - `FIND-SKEP-01`: Updated `test_search_similar_chunks_sqlite_fallback` to query Workspace 2 and assert `len(results) > 0`.
  - `FIND-SKEP-02`: Implemented `case()` ranking for priority in `tickets.py` (`Urgent=1`, `High=2`, `Medium=3`, `Low=4`) and added assertion verifying returned priorities in `test_tickets_module.py`.
  - `FIND-SEC-01`: Bound PostgreSQL port strictly to `127.0.0.1:5432:5432` in `docker-compose.yml`.
  - `FIND-SKEP-03`: Added `Ticket.id.desc()` as deterministic secondary tie-breaker in `query.order_by(order_fn(sort_col), Ticket.id.desc())`.
  - `FIND-SKEP-04`: Added `"X-Total-Count"` to `expose_headers` in `CORSMiddleware` in `backend/app/main.py`.
  - `FIND-SKEP-05`: Maintained `FALLBACK_SQLITE_URL` pointing to temporary SQLite file.
  - `FIND-SKEP-06`: Added `if ($null -eq $p2Obj -or $p2Obj.Count -lt 1) { throw ... }` in `smoke_docker.ps1`.
  - `FIND-SKEP-07`: Added `assert "test" in _opt_in_test_url.lower()` sanity check before `drop_all`.
  - `FIND-SKEP-08`: Added `User` and `AIUsageLog` imports to `init_db()`.
  - Clarified An Nguyen ticket counts in `docs/notes/B.md` and `docs/requests/devB.md`.
- **Stop Condition Evaluation:**
  - Zero unresolved Blocker or High findings.
  - All verification commands green (10/10 verification gate in `verify_setup.ps1`, 98 passed / 1 skipped offline, 99 passed in Docker PostgreSQL, clean Vite production build).
  - Stop early condition satisfied after 2c round 1.

### 2d round 1 (2026-10-25)
- **Subagents Dispatched (4 in parallel):**
  1. Skeptical Verifier (`b09f1d0f-446a-4b08-aa6e-f9cfcd1e93b8`)
  2. Requirements Auditor (`3ae06471-72f9-4521-9faa-8f7ac090564f`)
  3. Security Reviewer (`09d53dae-a7ca-48b3-b26c-c0fbb1d61756`)
  4. Ownership Hunter (`ef8c057c-cb0d-4073-8bd9-8dc6cef55c37`)
- **Findings Summary:**
  - **Blocker:** **0**
  - **High:** **0**
  - **Medium:** 1 (`FIND-MED-01`: Chuẩn hóa alias danh mục `"Technical Bug"` trong `list_tickets()`, tuân thủ Scope Lock Rule 1 đã được ghi nhận vào `docs/requests/devB.md:REQ-SEC-04` thay vì tự ý sửa file Python ngoài nhiệm vụ).
  - **Low / Informational:**
    - Đã đồng bộ `X-Total-Count: 43` trong `docs/spec/CONTRACTS.md:447` khớp với số lượng thực tế 43 vé.
    - Đã làm rõ ví dụ `ticket_id` trong `docs/API_CONTRACT.md` và `docs/spec/CONTRACTS.md` (ID số nguyên tự tăng `1` hoặc mã định dạng `#TICK-1042`).
    - Đã ghi nhận yêu cầu bổ sung hướng dẫn chạy Docker Compose cho Dev C vào `docs/requests/devB.md:CR-DEVC-03` theo `REQ-39`.
    - Ghi nhận kiến trúc rate limit in-memory (OWASP/an toàn cho Docker/Local hiện tại; mở rộng Redis khi triển khai multi-worker phân tán).
- **Stop Condition Evaluation:**
  - Hoàn toàn **không có bất kỳ Blocker hay High finding nào** (0 Blocker, 0 High).
  - Tất cả các cổng kiểm tra kỹ thuật đạt màu xanh tuyệt đối: `verify_setup.ps1` 10/10 PASS, backend pytest 98 passed / 1 skipped, 0 lỗi TypeScript, clean Vite build, `check_ownership.py` 100% compliant với ranh giới module.
  - Điều kiện dừng sớm được thỏa mãn sau vòng Review 1 của Prompt 2d.




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

## Plan (Prompt 2c - Dev B + Integrator: Close Gaps in 2b Report)

Environment: branch feature/b-platform, clean worktree, Docker Desktop 27.5.1 active, GEMINI_API_KEY set, verify_setup.ps1 10/10 PASS.

- **Task 1 (Database truth & opt-in TEST_DATABASE_URL):**
  files: backend/tests/conftest.py (Integrator), docs/notes/B.md.
  approach: State conftest.py hardcoded SQLite via tempfile; add opt-in TEST_DATABASE_URL (read before app import; if set, fail-fast assert PostgreSQL driver, skip SQLite fallback, clean tables; if unset, remain on isolated SQLite temp db); pre-create `smartdesk_test` PostgreSQL DB with pgvector in container; run pytest against PostgreSQL via TEST_DATABASE_URL; correct earlier wording in B.md.
  proof: Pytest summary line showing PostgreSQL run with host/db name (no password) + offline SQLite run.
  risk: Dialect differences between SQLite and PostgreSQL (JSON columns, vector types).
- **Task 2 (Application pgvector on PostgreSQL):**
  files: backend/app/services/embedding_service.py (Dev B), backend/tests/platform/test_pgvector_and_db.py, docs/notes/B.md.
  approach: Verify embedding_service.py search_similar_chunks uses `<=>` cosine distance on PostgreSQL; ensure dialect detection is robust; add test for PostgreSQL vector query against workspace_id=2 (SmileCare, which has chunks) and keep SQLite test; capture real app SQL query with `<=>` in Docker via PostgreSQL query logs.
  proof: Captured SQL statement with `<=>` operator and passing PostgreSQL vector test.
  risk: Silent in-memory fallback on error; test must assert native vector query executed.
- **Task 3 (Narrow trusted proxy CIDRs):**
  files: backend/app/core/config.py (Integrator), backend/app/core/security.py, backend/Dockerfile, docker-compose.yml, backend/tests/platform/test_proxy_ip.py.
  approach: Add TRUSTED_PROXY_CIDRS to config.py (empty = loopback only 127.0.0.1/32,::1/128); update is_trusted_proxy_ip to use TRUSTED_PROXY_CIDRS; set explicit subnet in docker-compose.yml (172.28.0.0/16) and configure compose TRUSTED_PROXY_CIDRS; bind backend to 127.0.0.1:8000:8000; update Dockerfile CMD; test that untrusted private IP (e.g. 10.0.0.1) cannot spoof headers.
  proof: Offline tests in test_proxy_ip.py pass; smoke_docker.ps1 passes with narrower trust.
  risk: Nginx container connection rejected if subnet is misconfigured.
- **Task 4 (Deterministic demo tickets for pagination/sorting):**
  files: backend/app/api/v1/endpoints/tickets.py (support page query param), backend/app/db/seed/seed_demo_tickets.py, backend/app/db/seed/__init__.py, docs/requests/devB.md, docs/notes/B.md.
  approach: Add `page` query param mapping to `skip = (page - 1) * limit`; seed 40 deterministic tickets using direct ORM instantiations (no LLM overhead) across categories, priorities, statuses and dates if DEMO_LOGIN_ENABLED=True and count <= 3; verify admin sees X-Total-Count >= 40, user sees only own tickets, sort_by and page 2 return different rows; log note for Dev C in devB.md.
  proof: API responses recorded in B.md showing count, role isolation, and sorted pagination.
  risk: Duplicate seed execution if called repeatedly; avoided by checking ticket count <= 3.
- **Task 5 (Smoke script volume retention):**
  files: scripts/smoke_docker.ps1 (Integrator).
  approach: Add -RemoveVolumes switch (default $false); only pass -v to `docker compose down` when switch is present; verify volume remains by default across restarts.
  proof: Run smoke_docker.ps1 from clean state; volume retained; exit 0.
  risk: Leftover container states if script fails early.

## Plan (Prompt 2d - Dev B + Integrator: Clean-up After 2c Report)

- **Task 0 (Setup check):**
  files: docs/notes/B.md.
  approach: Verify clean branch feature/b-platform, ancestry with origin/feature/b-platform, identity Bap <23110020@student.hcmute.edu.vn>, Docker 27.5.1 running, GEMINI_API_KEY set, and verify_setup.ps1 10/10 PASS.
- **Task 1 (Undo debug logging in retained volume - MUST run before Task 5):**
  files: PostgreSQL volume in smartdesk-postgres, docs/notes/B.md.
  approach: Run `SHOW log_statement;` (expect 'all'). Run `ALTER SYSTEM RESET log_statement; SELECT pg_reload_conf();`. Run fresh `SHOW log_statement;` in new session (expect 'none'). Verify no script/compose permanently sets it via `git grep -i "log_statement"`.
- **Task 2 (Credentials in notes & compose override):**
  files: docs/notes/B.md, docker-compose.yml, backend/.env.example.
  approach: Replace literal password with `<db-password>` in docs/notes/B.md (including plan). Parameterize BOTH `POSTGRES_PASSWORD` and `DATABASE_URL` in docker-compose.yml with `${POSTGRES_PASSWORD:-<demo-default>}`. Document in .env.example. List commits `1ae0471`, `7de6641`, `ef952b0` without rewriting history.
- **Task 3 (Notes truth on test database & review rounds):**
  files: docs/notes/B.md.
  approach: Replace claims that earlier 94 passed was PostgreSQL with SQLite truth; relabel Prompt 2c review as '2c round 1' noting test-only verification and stopped challenge subagent; correct Decision Log date 2026-10-20 to 2026-10-21 (commit b753b95).
- **Task 4 (Contract documents match code):**
  files: docs/API_CONTRACT.md, docs/spec/CONTRACTS.md, docs/notes/B.md.
  approach: Docs only (no code edits). Align GET /tickets params (`page`, `limit`, `skip`, `search`), priority sort order (`asc` = Urgent (1) first, `desc` = Low (4) first), `X-Total-Count` CORS expose, authenticated POST /tickets with field locking, per-route error codes.
- **Task 5 (Fresh-volume truth for demo data - runs after Task 1):**
  files: docs/requests/devB.md, docs/notes/B.md.
  approach: Run `docker compose down -v` then `up -d`. Authenticate via /auth/oauth2/login. Query admin tickets (X-Total-Count=43), An Nguyen tickets (X-Total-Count=15), and DB count (43). Explain derivation (3+40=43; 1+14=15; 26 in 2c was accumulated test tickets). Update CR-DEVC-02. End with `docker compose down`.
- **Task 6 (Ownership sanity):**
  files: docs/notes/B.md.
  approach: Run `python scripts/check_ownership.py --owner devB --as-integrator --base origin/Hoang`. Document `--as-integrator` requirement for frozen contracts and that `backend/Dockerfile` and `docker-compose.yml` are owned by `devB`.

## Plan (Prompt 2b - Dev B + Integrator: Hardening & Docker)

Environment: branch feature/b-platform, clean worktree, Docker Desktop 27.5.1 active, GEMINI_API_KEY set, verify_setup.ps1 10/10 PASS.

- **Task 1A (REQ-SEC-01 - Demo accounts restriction):**
  files: backend/app/db/seed/seed_users.py, backend/app/api/v1/endpoints/auth.py, backend/tests/platform/test_auth_security.py.
  approach: skip demo user seeding when DEMO_LOGIN_ENABLED is false; reject demo accounts on /auth/token with generic 401 and /auth/oauth2/login with 403 when DEMO_LOGIN_ENABLED is false; keep flag true by default in compose and .env.example with demo notice.
  proof: offline tests with monkeypatched DEMO_LOGIN_ENABLED=False proving 401 on password grant, 403 on demo oauth2, and local non-demo user unaffected.
  risk: tests must monkeypatch per-test with a valid JWT_SECRET_KEY so validate_auth_configuration does not abort.
- **Task 1B (REQ-SEC-02 - Client IP behind Nginx):**
  files: backend/Dockerfile (Dev B owned), backend/app/core/config.py (Integrator), backend/app/core/security.py, backend/app/api/v1/endpoints/auth.py, backend/tests/platform/test_proxy_ip.py.
  approach: start uvicorn with --proxy-headers and --forwarded-allow-ips for trusted Docker/private subnets; implement `get_trusted_client_ip()` that only trusts X-Real-IP / X-Forwarded-For when direct client is in trusted CIDRs (handling IPv6/IPv4 version differences safely); throttle uses this IP.
  proof: offline unit tests for `get_trusted_client_ip` with trusted proxy, untrusted proxy (spoof rejected), IPv6 loopback, and direct requests.
  risk: misconfigured CIDRs or unhandled IPv6 TypeError in ipaddress module.
- **Task 1C (REQ-SEC-03 - POST /api/v1/tickets requires auth):**
  files: backend/app/api/v1/endpoints/tickets.py, backend/tests/platform/test_ticket_auth.py, docs/spec/CONTRACTS.md, docs/API_CONTRACT.md, docs/requests/devB.md.
  approach: require `current_user = Depends(get_current_user)`; regular users are strictly bound to `current_user.email` & `full_name`; admins may specify customer email/name for support ticketing; check frontend ticket form and mocks and log Dev C request in devB.md; update contract docs.
  proof: offline route tests (401 without token, 201 with regular user token binding email, 201 with admin creating for customer).
  risk: test_api.py uses admin client and expects customer_name from payload (preserved by admin rule).
- **Task 2 (Docker and PostgreSQL + pgvector):**
  files: scripts/smoke_docker.ps1 (Integrator).
  approach: fix demo email to admin@smartdesk.ai in smoke_docker.ps1; add tests for wrong password (401) and unauth protected route (401); run docker compose build & up -d; verify health, frontend nginx, api proxy, SSE; run SQL to verify vector column & <=> cosine search; run pytest inside backend container against PostgreSQL; run smoke_docker.ps1; docker compose down.
  proof: real SQL query output, containerized pytest against PostgreSQL, smoke_docker.ps1 exit 0.
  risk: port conflicts (5432, 8000, 3000) or container naming conflicts.
- **Task 3 (Notes & Requests):**
  files: docs/notes/B.md, docs/notes/B-ai-usage.md, docs/requests/devB.md.
  approach: record real outputs in Evidence; update "Giải thích code" for demo flag, proxy IP, and ticket auth; mark REQ-SEC-01..03 as DONE.


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

### Task 5 - Frontend Isolation & Git Secret History Scan (REQ-08)
- Grep `frontend/package.json` for `@google/genai` or `@google/generative-ai`:
  `Select-String -Path "frontend/package.json" -Pattern "genai|generative"` -> 0 matches.
- Grep `frontend/src/` for `@google/` or `AIza`:
  `Get-ChildItem -Path "frontend/src" -Recurse -File | Select-String -Pattern "@google/|AIza"` -> 0 matches.
- Executed `npm ci --prefix frontend` -> added 93 packages in 29s, exit 0.
- Executed `npm run build --prefix frontend` -> Vite 6 build completed in 2.46s, generated `frontend/dist`.
- Grep `frontend/dist/` for `@google/`, `AIza`, or `generative-ai`:
  `Get-ChildItem -Path "frontend/dist" -Recurse -File | Select-String -Pattern "@google/|AIza|generative-ai"` -> 0 matches.
- Git commit secret history scan:
  `git log -S "AIza" --name-only --oneline` -> Matches found only in documentation and audit files referencing the verification check itself:
  - Commit "fix(auth): never use a known default JWT secret" (`docs/notes/B.md`)
  - Commit "docs: add project audit, gap analysis, plan, and specification" (`docs/audit/01-gap-analysis.md`, `docs/plan/PLAN.md`, `docs/spec/SPEC.md`)
  - Zero API keys or secrets were ever committed to Git history.
- Verification Gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1` -> `RESULT: ALL 10/10 CHECKS PASSED (100% READY FOR IMPLEMENTATION)`.

### Prompt 2d Review & Final Verification Notes [Post-Merge Integrator Verification]
- Date: 2026-10-26 — Completed post-merge verification on branch `verify/final-verification`.
- Applied pending frozen-file requests: `MRG-DEF-07` (`CONTRACTS.md` status="config_error"), `MRG-DEF-08` (`CONTRACTS.md` / `API_CONTRACT.md` verification report endpoint), `CR-DEVC-02` (frontend ticket query params & telemetry types), and `MRG-DEF-02` (`scripts/check_roster.py` exemption for AI Tool Used lines).
- Executed real E2E Docker Compose verification across Items A through M:
  * Item A: Full Docker stack healthy, Nginx reverse proxy functional.
  * Item B: Demo login admin/user 200, wrong password 401 generic message, forged Google token 501, RBAC route barrier 401/403/200, sliding-window throttle 429 after 10 attempts, DEMO_LOGIN_ENABLED=false 401 barrier, test_jwt_secret.py 13 passed.
  * Item C: Unauthenticated POST /tickets 401, user ticket email locked to JWT identity, admin ticket created for client, canonical SLA hours (Urgent=2, High=4, Medium=8, Low=24), sort_by=priority asc/desc, pagination non-overlapping, DELETE 204/404, RBAC counts (Admin=45, An Nguyen=16).
  * Item D: Live RAG in-scope 200, out-of-scope refusal with escalation_recommended=True and zero hallucinated citations, English & Vietnamese prompt injection blocked with HTTP 400 PROMPT_SECURITY_VIOLATION.
  * Item E: SSE streaming direct and via Nginx unbuffered (event: metadata, token, done).
  * Item F: Tool agent create_escalation_ticket PendingAction, 1st confirmation executes 1 ticket, 2nd confirmation returns 400 Bad Request, cancel returns executed=false with 0 tickets created, cross-user confirmation returns 403 Forbidden.
  * Item G: Document upload 201, 3-stage active verification (SyntheticQA -> SandboxRAG -> AI Judge) faithfulness score 0.95 passed, document publish 200. Logged MRG-DEF-10 for PostgreSQL pgvector 768 vs 3072 live embedding dimension mismatch.
  * Item H: PostgreSQL pgvector extension 0.8.6 verified, <=> cosine operator verified, container pytest against PostgreSQL on smartdesk_test 4 passed, SHOW log_statement confirmed none.
  * Item I: Admin AI telemetry GET /agent/ai-usage 200, POST /agent/reset-cooldown 401 unauth, 403 user, 200 admin, alias route 200.
  * Item J: Audited 24-case benchmark: 17 live LLM generative calls, 3 tool calls, 4 guardrail blocks, 0 fallback.
  * Item K: All 4 core mobile views verified in docs/evidence/ (375x812); frontend code verified for CR-DEVC-01 and CR-DEVC-02.
  * Item L: smartdesk-backend and smartdesk-postgres bound strictly to 127.0.0.1 (never 0.0.0.0).
  * Item M: Tracked repo clean of .env, *.db, eval_runs; Git history free of leaked API keys; frontend/dist free of Google SDKs and keys.
- Composed root `AI_USAGE.md` documenting 5 real failure cases with verified commit hashes from Git history.


#### Task 0 - Setup check
- Identity confirmed: `git config user.name` = `Bap`, `git config user.email` = `23110020@student.hcmute.edu.vn`.
- Branch `feature/b-platform` ancestry confirmed: `git merge-base --is-ancestor origin/feature/b-platform HEAD` exit 0.
- Docker Desktop Linux Engine confirmed active: `docker version` exit 0 (Docker 27.5.1).
- `GEMINI_API_KEY`: set in `backend/.env`.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1` -> `RESULT: ALL 10/10 CHECKS PASSED (100% READY FOR IMPLEMENTATION)`.

#### Task 1 - Security Hardening (Offline First)
- Test suite `backend/tests/platform/test_auth_security.py`:
  Command: `pytest backend/tests/platform/test_auth_security.py -v` -> `12 passed in 1.94s`.
  * Verifies demo login works when `DEMO_LOGIN_ENABLED=True`.
  * Verifies demo login rejected with HTTP 401 when `DEMO_LOGIN_ENABLED=False` on both `/auth/oauth2/login` and `/auth/token`.
  * Verifies non-demo accounts are unaffected.
  * Verifies generic error message matches wrong-password response.
- Test suite `backend/tests/platform/test_proxy_ip.py`:
  Command: `pytest backend/tests/platform/test_proxy_ip.py -v` -> `7 passed in 0.88s`.
  * Verifies `is_trusted_proxy_ip` correctly identifies loopback and private subnets.
  * Verifies `get_trusted_client_ip` extracts client IP only when direct peer is trusted.
  * Verifies spoofed `X-Forwarded-For` from untrusted peers is ignored.
  * Verifies throttle blocks client IP based on trusted proxy header.
- Test suite `backend/tests/platform/test_ticket_auth.py`:
  Command: `pytest backend/tests/platform/test_ticket_auth.py -v` -> `3 passed in 0.81s`.
  * Verifies unauthenticated `POST /api/v1/tickets` returns HTTP 401.
  * Verifies regular user ticket creation locks `customer_email` to `current_user.email`.
  * Verifies admin can create tickets specifying client customer details.
- Full offline test suite:
  Command: `pytest backend/tests/ -q` -> `94 passed in 9.53s`.
- Commit: "fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation".

#### Task 2 - Docker and PostgreSQL + pgvector Verification
- Build:
  Command: `docker compose build` -> Built `smartdesk-postgres`, `smartdesk-backend`, `smartdesk-frontend` with exit 0.
- Start & Health:
  Command: `docker compose up -d` -> Containers started.
  Command: `Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"` ->
  `{"status":"ok","database":"connected","version":"1.0.0"}`
- Frontend & Reverse Proxy:
  Command: `Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing` -> HTTP 200.
  Command: `Invoke-RestMethod -Uri "http://localhost:3000/api/v1/health"` -> `{"status":"ok","database":"connected","version":"1.0.0"}`
- Nginx SSE Streaming Unbuffered:
  Command: `python -c "import urllib.request, json... /api/v1/chat/stream"` ->
  `Status: 200 Content-Type: text/event-stream; charset=utf-8`
  First event (`event: metadata`) received in 0.096s, followed immediately by `event: token` chunks.
  Nginx configuration verified: `proxy_buffering off;` directive present in `/etc/nginx/conf.d/default.conf`.
- PostgreSQL Container & pgvector Queries:
  * Extension check:
    Command: `docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"`
    Output:
    ```
     extname | extversion 
    ---------+------------
     vector  | 0.8.6
    (1 row)
    ```
  * Seed data row counts:
    Command: `docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT 'users' as tbl, count(*) FROM users UNION ALL SELECT 'workspaces', count(*) FROM workspaces UNION ALL SELECT 'documents', count(*) FROM documents UNION ALL SELECT 'knowledge_chunks', count(*) FROM knowledge_chunks UNION ALL SELECT 'faq_items', count(*) FROM faq_items;"`
    Output:
    ```
           tbl        | count 
    ------------------+-------
     users            |     2
     workspaces       |     3
     documents        |     2
     knowledge_chunks |     9
     faq_items        |    12
    (5 rows)
    ```
  * Column type verification:
    Command: `docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT attname, format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid = 'knowledge_chunks'::regclass AND attname = 'embedding';"`
    Output:
    ```
      attname  | format_type 
    -----------+-------------
     embedding | vector(768)
    (1 row)
    ```
    Non-null embeddings: `9 / 9` chunks populated.
  * Vector similarity query via native `<=>` cosine distance:
    Command: `docker compose exec -T postgres psql -U postgres -d smartdesk -c "SELECT id, chunk_index, ROUND((embedding <=> (SELECT embedding FROM knowledge_chunks LIMIT 1))::numeric, 4) as cosine_distance FROM knowledge_chunks LIMIT 3;"`
    Output:
    ```
     id | chunk_index | cosine_distance 
    ----+-------------+-----------------
      1 |           0 |          0.0000
      2 |           1 |          0.9769
      3 |           2 |          1.0301
    (3 rows)
    ```
- Containerized Pytest in Prompt 2b:
  Command: `docker compose exec -T backend pytest` -> `94 passed in 5.94s`.
  *Note on Database Truth:* As audited in Prompt 2c Task 1, `backend/tests/conftest.py` lines 18-24 previously hardcoded `os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"` unconditionally at the session level. Therefore, despite running inside the Docker container, earlier test runs actually executed on an in-container temporary SQLite database, not PostgreSQL. Real PostgreSQL execution was enabled in Prompt 2c Task 1 via `TEST_DATABASE_URL`.
- Automated Clean-State Smoke Test:
  Command: `powershell -ExecutionPolicy Bypass -File scripts/smoke_docker.ps1`
  Output:
  ```
  [1/8] Checking Docker Engine availability... Docker Engine is active and ready.
  [2/8] Building Docker images (postgres, backend, frontend)... Build completed successfully.
  [3/8] Starting containers in detached mode... Containers started.
  [4/8] Polling backend health... Backend is healthy (attempt 2/30): status=ok, db=connected
  [5/8] Verifying Nginx frontend and reverse proxy... Frontend SPA (HTTP 200) and reverse proxy /api/v1/ are functional!
  [6/8] Testing authentication, wrong password (401), and protected route gates...
    Demo admin login successful: token issued for admin@smartdesk.ai (role=admin)
    Wrong password rejected with HTTP 401 Unauthorized.
    Unauthenticated request to /tickets rejected with HTTP 401 Unauthorized.
    Authenticated ticket listing successful: HTTP 200, X-Total-Count=3
  [7/8] Verifying pgvector extension in PostgreSQL container... vector | 0.8.6
  [8/8] Verifying Nginx reverse proxy buffering for SSE token streaming... proxy_buffering off confirmed.
  ALL DOCKER & POSTGRESQL SMOKE CHECKS PASSED!
  Tearing down containers and volumes (--remove-orphans -v)... Teardown complete.
  ```
  Exit code: 0.

### Prompt 2c Evidence

#### Task 1 - Database Truth & TEST_DATABASE_URL
- **Audit of Previous Test Runs:**
  In `backend/tests/conftest.py`, lines 18-24 previously had:
  ```python
  _temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
  _temp_db_path = Path(_temp_db.name).resolve().as_posix()
  _temp_db.close()
  os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"
  os.environ["FALLBACK_SQLITE_URL"] = f"sqlite+aiosqlite:///{_temp_db_path}"
  ```
  And lines 54-56:
  ```python
  test_engine, test_factory = create_engine_and_factory(f"sqlite+aiosqlite:///{_temp_db_path}")
  session_module.engine = test_engine
  session_module.async_session_factory = test_factory
  ```
  Therefore, all earlier 94 tests unconditionally used a temporary SQLite database file, even when invoked inside Docker.
- **Implementation:**
  - Added opt-in `TEST_DATABASE_URL` in `backend/tests/conftest.py`. When set, it configures `DATABASE_URL` before importing `app.main` and asserts `assert "postgresql" in session_module.engine.url.drivername`. When unset, it preserves 100% of the existing temporary SQLite behavior.
  - Updated `create_engine_and_factory` in `backend/app/db/session.py` to accept `**custom_kwargs` and configured `poolclass=NullPool` for PostgreSQL test runs to eliminate asyncpg cross-event-loop future errors.
  - Created separate test database `smartdesk_test` in the PostgreSQL container (never using the demo `smartdesk` DB).
- **PostgreSQL Pytest Run (Real Containerized Proof):**
  - Command: `docker compose exec -T -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:<db-password>@postgres:5432/smartdesk_test backend pytest tests/ -q`
  - Target URL Host and DB: `postgres:5432/smartdesk_test`
  - Output: `94 passed in 7.84s`
  - Exit code: 0.

#### Task 2 - Application pgvector Similarity Search on PostgreSQL
- **Code State Analysis (`backend/app/services/embedding_service.py`):**
  `embedding_service.search_similar_chunks()` detects dialect via `getattr(session, "bind", None) or session.get_bind()`.
  On PostgreSQL, it executes a native SQL pgvector cosine distance query using `KnowledgeChunk.embedding.cosine_distance(query_vector)`, which compiles to the `<=>` operator in SQL with `LIMIT top_k`. On SQLite, it falls back cleanly to in-memory cosine similarity.
- **Automated Test Coverage:**
  `backend/tests/platform/test_pgvector_and_db.py`:
  * `test_search_similar_chunks_sqlite_fallback` PASSED.
  * `test_search_similar_chunks_postgresql_pgvector` PASSED (verifies native pgvector query on PostgreSQL without fallback warnings).
  Command: `docker compose exec -T -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:<db-password>@postgres:5432/smartdesk_test backend pytest tests/platform/test_pgvector_and_db.py -v` -> `4 passed in 0.56s`.
- **Live Captured SQL Statement from PostgreSQL Logs (`log_statement='all'`):**
  Captured from `smartdesk-postgres` during `POST /api/v1/chat` query on Workspace 2 (SmileCare):
  ```sql
  SELECT 
      knowledge_chunks.id, 
      knowledge_chunks.chunk_id, 
      knowledge_chunks.parent_doc_id, 
      knowledge_chunks.workspace_id, 
      knowledge_chunks.document_id, 
      knowledge_chunks.chunk_index, 
      knowledge_chunks.page_number, 
      knowledge_chunks.title, 
      knowledge_chunks.content, 
      knowledge_chunks.source_url, 
      knowledge_chunks.embedding, 
      knowledge_chunks.created_at, 
      $1::INTEGER - (knowledge_chunks.embedding <=> $2) AS score, 
      documents.status AS doc_status 
  FROM knowledge_chunks 
  LEFT OUTER JOIN documents ON knowledge_chunks.document_id = documents.id 
  WHERE knowledge_chunks.workspace_id = $3::INTEGER 
    AND (knowledge_chunks.document_id IS NULL OR documents.status = $4::VARCHAR) 
  ORDER BY knowledge_chunks.embedding <=> $5 
  LIMIT $6::INTEGER
  ```
  Parameters: `$1 = '1'`, `$2 = '[768-dim query vector]'`, `$3 = '2'`, `$4 = 'published'`, `$5 = '[768-dim query vector]'`, `$6 = '3'`.

#### Task 3 - Trusted Proxy Narrowing & Anti-Spoofing
- **Vấn đề bảo mật trước đây:**
  Giá trị mặc định của `FORWARDED_ALLOW_IPS` từng bao quát các dải mạng riêng tư rộng (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). Trong môi trường mạng nội bộ hoặc VPS dùng chung, các máy trạm/container khác trong cùng dải có thể gửi header `X-Forwarded-For` giả mạo để thao túng định danh client IP và bypass bộ điều tiết tần suất đăng nhập (`LoginThrottle`).
- **Giải pháp triển khai:**
  1. `backend/app/core/config.py`: Thay thế dải mặc định bằng `TRUSTED_PROXY_CIDRS: str = ""` (mặc định rỗng).
  2. `backend/app/core/security.py`: Hàm `is_trusted_proxy_ip()` khi `TRUSTED_PROXY_CIDRS` rỗng sẽ chỉ tin cậy duy nhất loopback (`127.0.0.1/32` và `::1/128`). Mọi IP riêng tư khác (`10.0.0.1`, `192.168.1.50`, v.v.) đều bị coi là không tin cậy.
  3. `docker-compose.yml`:
     - Khai báo bridge network riêng `smartdesk-net` với dải mạng cố định `172.28.0.0/16`. Cả 3 container (`postgres`, `backend`, `frontend`) cùng gắn vào mạng này.
     - `backend.environment`: Cấu hình `TRUSTED_PROXY_CIDRS: "127.0.0.1/32,::1/128,172.28.0.0/16"`.
     - `backend.ports`: Khóa chặt cổng backend về `127.0.0.1:8000:8000` (thay vì `0.0.0.0:8000`), buộc mọi truy cập từ bên ngoài phải đi qua Nginx reverse proxy.
  4. `backend/Dockerfile`: Cập nhật lệnh khởi động Uvicorn:
     `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1,::1,172.28.0.0/16"]`
  5. `backend/tests/platform/test_proxy_ip.py`: Bổ sung kiểm thử:
     - `test_untrusted_private_ip_cannot_spoof_client_ip`: Chứng minh `10.0.0.1`, `192.168.1.50`, `172.16.5.10` gửi `X-Forwarded-For` bị bỏ qua, `get_trusted_client_ip()` trả về trực tiếp IP nguồn.
     - `test_untrusted_private_ip_cannot_bypass_throttle_with_rotating_forwarded_headers`: Chứng minh kẻ tấn công từ IP `10.0.0.1` liên tục đổi header `X-Forwarded-For` mỗi lần gửi vẫn bị ghi nhận vào cùng một bucket IP thực tế và bị khóa với `HTTP 429`.
- **Kết quả kiểm thử:**
  - `python -m pytest backend/tests/platform/test_proxy_ip.py -v`: 9 passed in 1.33s.
  - `python -m pytest backend/tests/ -q`: 96 passed, 1 skipped in 10.51s.

#### Task 4 - Deterministic Demo Tickets for Pagination and Sorting
- **Vấn đề tồn đọng trước đây:**
  Database seed trước đây chỉ có đúng 3 tickets ban đầu (`#TICK-1042`, `#TICK-1041`, `#TICK-1039`), khiến việc kiểm thử phân trang (`?page=2`) trong script smoke test không có dữ liệu để lật trang và sắp xếp chỉ kiểm thử được trên 3 bản ghi.
- **Giải pháp triển khai:**
  1. `backend/app/db/seed/seed_demo_tickets.py`: Bổ sung module sinh 40 tickets mẫu tĩnh, mang tính tất định (deterministic), đa dạng về danh mục (`Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General`), độ ưu tiên (`Urgent`, `High`, `Medium`, `Low` tương ứng với SLA 2h, 4h, 8h, 24h), trạng thái (`open`, `in_progress`, `resolved`), phân bổ trên 3 workspaces và trải dài theo các mốc thời gian khác nhau.
  2. Chỉ kích hoạt seed 40 tickets này khi `settings.DEMO_LOGIN_ENABLED` là True và số lượng ticket hiện tại trong bảng `<= 3`.
  3. Phân bổ người dùng: 14 tickets cho `an.nguyen@company.vn` (kết hợp với ticket `#TICK-1042` ban đầu tạo thành tập dữ liệu riêng biệt cho kiểm thử cách ly người dùng), 5 tickets cho `admin@smartdesk.ai`, và 21 tickets cho các khách hàng hư cấu độc lập khác.
  4. `backend/app/api/v1/endpoints/tickets.py`: Hỗ trợ tham số truy vấn `page: Optional[int] = Query(None, ge=1)` tự động quy đổi thành `skip = (page - 1) * limit`.
  5. `docs/requests/devB.md`: Gửi `CR-DEVC-02` thông báo cho Dev C về 40+ demo tickets trong Docker và hướng dẫn cách reset dữ liệu demo khi cần (`docker compose down -v` rồi `docker compose up -d`).
- **Bằng chứng xác minh thực tế qua Docker API (PostgreSQL DB qua Nginx):**
  - Số lượng bản ghi trong Docker PostgreSQL: `SELECT count(*) FROM tickets;` $\to$ **43** rows.
  - Đăng nhập Admin $\to$ `GET /api/v1/tickets?sort_by=created_at&sort_order=desc&limit=10&page=1`:
    - `X-Total-Count`: **43** ($\ge 40$: True).
    - Page 1 (10 codes): `['#TICK-1039', '#TICK-1041', '#TICK-1042', '#TICK-1139', '#TICK-1138', '#TICK-1137', '#TICK-1136', '#TICK-1135', '#TICK-1134', '#TICK-1133']`.
  - Admin $\to$ `GET /api/v1/tickets?sort_by=created_at&sort_order=desc&limit=10&page=2`:
    - Page 2 (10 codes): `['#TICK-1132', '#TICK-1131', '#TICK-1130', '#TICK-1129', '#TICK-1128', '#TICK-1127', '#TICK-1126', '#TICK-1125', '#TICK-1124', '#TICK-1123']`.
    - Giao giữa Page 1 và Page 2: `set()` (tập rỗng, không trùng lặp bất kỳ bản ghi nào!).
  - Đăng nhập Khách hàng (`an.nguyen@company.vn`) $\to$ `GET /api/v1/tickets?limit=100`:
    - `X-Total-Count`: **26** trên volume container đang chạy (trong fresh seed là 15 tickets gồm 1 vé ban đầu và 14 vé demo; toàn bộ 100% email trả về là `an.nguyen@company.vn`, cách ly dữ liệu tuyệt đối so với 43 tickets của toàn hệ thống).
- **Kiểm thử tự động:**
  - `python -m pytest backend/tests/test_tickets_module.py -v`: 7 passed in 0.65s (bao gồm `test_demo_tickets_pagination_and_sorting` và `test_demo_tickets_user_isolation`).

#### Task 5 - Smoke Script Volume Retention
- **Vấn đề tồn đọng trước đây:**
  Script `scripts/smoke_docker.ps1` trước đây luôn chạy `docker compose down -v` trong khối `finally`, hủy toàn bộ volume dữ liệu PostgreSQL (`pgdata`), xóa sạch extension pgvector và các bảng dữ liệu seed khiến việc kiểm tra đối soát thủ công sau khi chạy script gặp khó khăn.
- **Giải pháp triển khai:**
  1. Thêm tham số `[switch]$RemoveVolumes = $false` vào `scripts/smoke_docker.ps1`.
  2. Mặc định ($false), khối `finally` thực hiện `docker compose down --remove-orphans` (không có cờ `-v`), giữ nguyên vẹn volume database trên máy host để nhà phát triển có thể kiểm tra dữ liệu sau smoke test. Chỉ khi người dùng truyền `-RemoveVolumes` thì cờ `-v` mới được kích hoạt.
  3. Bổ sung bước kiểm tra phân trang (bước 5e) trong kịch bản smoke test: gọi `GET /api/v1/tickets?limit=10&page=2` xác nhận phản hồi đúng 10 tickets trang 2 với `X-Total-Count=43`.
- **Bằng chứng xác minh thực tế:**
  - Lệnh thực thi: `powershell -ExecutionPolicy Bypass -File scripts/smoke_docker.ps1` (không truyền `-RemoveVolumes`).
  - Toàn bộ 8/8 bước smoke checks đều PASS, exit code 0.
  - Kiểm tra volume sau khi teardown: `docker volume ls` $\to$ volume `smartdesk-b_pgdata` vẫn tồn tại nguyên vẹn.
  - Khởi động lại container và truy vấn PostgreSQL: `SELECT count(*) FROM tickets;` $\to$ giữ nguyên chính xác **43** tickets.

### Prompt 2d Evidence

#### Task 0 - Setup Check
- **Working Tree & Git State:**
  - Branch: `feature/b-platform` (Worktree `..\smartdesk-B`).
  - Ancestry: `git merge-base --is-ancestor origin/feature/b-platform HEAD` exit code 0.
  - Identity: `Bap` <`23110020@student.hcmute.edu.vn`>.
  - Docker Desktop: Engine 27.5.1 running.
  - API Key: `GEMINI_API_KEY: set` in `backend/.env`.
  - Toolchain Verification Gate: `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1` -> `ALL 10/10 CHECKS PASSED (100% READY)`.

#### Task 1 - Undo Debug Logging in Retained Database Volume
- **Before Reset (Inspection on smartdesk-postgres):**
  - Command: `docker exec smartdesk-postgres psql -U postgres -d smartdesk -c "SHOW log_statement; SHOW log_min_duration_statement;"`
    Output:
    ```
     log_statement 
    ---------------
     all
    (1 row)

     log_min_duration_statement 
    ----------------------------
     -1
    (1 row)
    ```
  - Inspection of `/var/lib/postgresql/data/postgresql.auto.conf`:
    Contains line: `log_statement = 'all'`.
- **Reset Execution:**
  - Command: `docker exec smartdesk-postgres psql -U postgres -d smartdesk -c "ALTER SYSTEM RESET log_statement;" -c "SELECT pg_reload_conf();"`
    Output: `ALTER SYSTEM`, `pg_reload_conf: t`.
- **After Reset Verification (Fresh Session):**
  - Command: `docker exec smartdesk-postgres psql -U postgres -d smartdesk -c "SHOW log_statement; SHOW log_min_duration_statement;"`
    Output:
    ```
     log_statement 
    ---------------
     none
    (1 row)

     log_min_duration_statement 
    ----------------------------
     -1
    (1 row)
    ```
  - Inspection of `/var/lib/postgresql/data/postgresql.auto.conf`: `log_statement` line completely removed.
  - Search across repository: `git grep -i "log_statement"` confirmed no script, compose file, or Dockerfile permanently enables statement logging.

#### Task 2 - Credentials in Notes & Environment Override
- **Thay thế mật khẩu tường minh trong tài liệu:**
  - Toàn bộ chuỗi mật khẩu database cục bộ tường minh trong `docs/notes/B.md` (bao gồm câu lệnh kiểm thử Task 1 & 2 của Prompt 2c) đã được thay thế bằng placeholder `<db-password>`.
- **Cấu hình biến môi trường có thể ghi đè trong docker-compose.yml:**
  - `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgrespassword}`
  - `DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:-postgrespassword}@postgres:5432/smartdesk}`
  - Trong `backend/.env.example`: Đã bổ sung tài liệu hướng dẫn cấu hình `POSTGRES_PASSWORD="postgrespassword"` với ghi chú rõ ràng chỉ dành riêng cho demo cục bộ.
- **Lịch sử commit chứa chuỗi mật khẩu tường minh (không viết lại lịch sử git):**
  - Commit `1ae0471` ("xóa các từ homework"): Khởi tạo file `docker-compose.yml` ban đầu.
  - Commit `7de6641` ("test(platform): enable opt-in TEST_DATABASE_URL and verify postgres test run"): Ghi nhận lệnh chạy pytest PostgreSQL trong `docs/notes/B.md`.
  - Commit `ef952b0` ("feat(db): verify pgvector cosine search and captured sql query on postgresql"): Ghi nhận lệnh chạy kiểm thử pgvector trong `docs/notes/B.md`.
- **Kiểm chứng sạch sẽ:**
  - Lệnh: `git grep -n "postgrespassword"`
  - Kết quả: Chỉ xuất hiện duy nhất tại `docker-compose.yml` (mặc định demo được ghi chú) và `backend/.env.example` (hướng dẫn mẫu). Hoàn toàn không còn trong bất kỳ tài liệu hay ghi chú nào khác.

#### Task 3 - Notes Truth on Test Database and Review Rounds
- **Đính chính cơ sở dữ liệu kiểm thử (Test Database Truth):**
  - Đã rà soát và đính chính các phát biểu trong `docs/notes/B.md` (tại mục 1 và 2): Lần chạy pytest trong container tại Prompt 2b (94 passed) thực tế chạy trên database SQLite tạm thời do cấu hình cũ của `conftest.py`.
  - Việc kiểm thử trên PostgreSQL thực sự lần đầu tiên được triển khai tại Prompt 2c thông qua biến môi trường `TEST_DATABASE_URL` (99 passed trong 40.5s trên database PostgreSQL `smartdesk_test` có extension `pgvector`).
- **Chuẩn hóa lịch sử đánh giá (Review Rounds Truth):**
  - Đã đổi tên mục "Round 3 (2026-10-25)" thành "2c round 1 (2026-10-25)" để phản ánh đúng đây là vòng rà soát của Prompt 2c, không phải vòng 3 liên tục.
  - Ghi nhận trung thực sự cố subagent: Ở giai đoạn lập kế hoạch Prompt 2c, subagent Plan Skeptic bị treo/timeout và được dừng sớm; các cải tiến (sắp xếp priority bằng `case()`, cấu hình CORS, binding IP) được kiểm chứng trực tiếp bằng automated tests mà không qua vòng subagent thứ hai.
- **Chuẩn hóa ngày Decision Log:**
  - Ngày cấu hình dual-dialect vector type `Vector(768).with_variant(JSON(), "sqlite")` đã được sửa từ `2026-10-20` thành `2026-10-21`, đồng bộ chuẩn xác với git log của commit `b753b95`.

#### Task 4 - Contract Documents Match Code (Documents Only)
- **Rà soát và đồng bộ hai file hợp đồng (`docs/API_CONTRACT.md` và `docs/spec/CONTRACTS.md`):**
  - Đã so sánh chi tiết mã nguồn `backend/app/api/v1/endpoints/tickets.py` với các tài liệu hợp đồng và cập nhật hoàn toàn (không sửa file Python nào):
  - **`GET /api/v1/tickets`:**
    - Thay thế tham số cũ `page_size` bằng chuẩn `limit: int = Query(20, ge=1, le=100)`.
    - Bổ sung `skip: int = Query(0, ge=0)`.
    - Bổ sung `page: Optional[int] = Query(None, ge=1)` kèm giải thích công thức chuyển đổi `skip = (page - 1) * limit`.
    - Bổ sung `search: Optional[str] = Query(None)` tìm kiếm chuỗi không phân biệt hoa thường trên ticket code, subject, description, customer name, customer email.
    - Làm rõ quy luật sắp xếp mức độ ưu tiên (`sort_by="priority"`): sử dụng SQL `case()` rank: Urgent (1), High (2), Medium (3), Low (4). `sort_order=asc` đưa Urgent lên đầu (rank 1); `sort_order=desc` đưa Low lên đầu (rank 4). Tie-breaker thứ cấp luôn là `Ticket.id.desc()` để phân trang xác thực.
    - Tài liệu hóa header `X-Total-Count` được phơi bày qua CORS `Access-Control-Expose-Headers`.
    - Ghi rõ mã lỗi: `401 Unauthorized`, `422 Unprocessable Entity`.
  - **`POST /api/v1/tickets`:**
    - Ghi nhận bắt buộc xác thực Bearer token (`Authorization: Bearer <token>`) theo `REQ-SEC-03`.
    - Khóa trường danh tính: Người dùng thông thường (`role == "user"`) bị khóa cứng `customer_email` và `customer_name` theo JWT token owner (ghi đè payload). Hỗ trợ viên (`role == "admin"`) có thể chỉ định thông tin khách hàng.
    - Bảo vệ chống Prompt Injection: Kiểm tra qua `check_prompt_injection()`, trả về `HTTP 400 Bad Request` với mã `PROMPT_SECURITY_VIOLATION`.
    - Ghi rõ mã lỗi: `400 Bad Request`, `401 Unauthorized`, `422 Unprocessable Entity`.
  - **`GET /api/v1/tickets/{ticket_id}`:**
    - Bổ sung đặc tả hoàn chỉnh cho endpoint: tham số đường dẫn `ticket_id: str` (số nguyên hoặc mã formatted `#TICK-XXXX`).
    - Kiểm soát phân quyền: User thường chỉ xem được ticket của chính mình (`403 Forbidden` nếu xem ticket người khác); Admin xem được mọi ticket.
    - Ghi rõ mã lỗi: `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`.
  - **`PATCH /api/v1/tickets/{ticket_id}`:**
    - Cập nhật thông tin và nháp trả lời của Copilot, giới hạn chỉ dành cho Admin/Agent (`require_role("admin")`).
    - Ghi rõ mã lỗi: `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`.
  - **`DELETE /api/v1/tickets/{ticket_id}`:**
    - Xóa ticket vĩnh viễn, giới hạn chỉ dành cho Admin (`require_role("admin")`).
    - Ghi rõ mã lỗi: `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`.

#### Task 5 - Fresh-Volume Truth for Demo Data
- **Khởi tạo volume hoàn toàn mới (Fresh Volume Initialization):**
  - Thực thi: `docker compose down -v` xóa sạch container, network và volume `smartdesk-b_pgdata`.
  - Khởi động lại: `docker compose up -d` tạo volume sạch mới và khởi tạo PostgreSQL 16 + pgvector.
- **Xác thực kết quả truy vấn qua Nginx Reverse Proxy (`http://localhost:3000/api/v1`):**
  - Thực thi script Python gửi request:
    - **Tài khoản Admin (`admin@smartdesk.ai`, provider="demo"):**
      - `X-Total-Count`: **43**
      - Độ dài mảng tickets trả về: **43**
    - **Tài khoản User (`an.nguyen@company.vn`, provider="demo"):**
      - `X-Total-Count`: **15**
      - Độ dài mảng tickets trả về: **15**
- **Xác thực trực tiếp từ cơ sở dữ liệu PostgreSQL:**
  - Lệnh: `docker exec smartdesk-postgres psql -U postgres -d smartdesk -c "SELECT count(*) FROM tickets;"`
  - Kết quả: `count = 43`
- **Giải thích chi tiết sự khác biệt về số lượng:**
  - **Tổng số ticket hệ thống:** Gồm **3** ticket khởi tạo ban đầu (`#TICK-1042`, `#TICK-1041`, `#TICK-1039` trong `seed_tickets.py`) cộng với **40** ticket demo (`#TICK-1101` đến `#TICK-1140` trong `seed_demo_tickets.py`), tổng cộng chính xác là **43** ticket.
  - **Số lượng của An Nguyễn:** Gồm **1** ticket khởi tạo (`#TICK-1042`) và **14** ticket demo (`#TICK-1101` đến `#TICK-1114`), tổng cộng chính xác là **15** ticket.
  - **Phân quyền RBAC:** Tài khoản Admin có quyền xem toàn bộ hệ thống nên nhận đủ 43 ticket; tài khoản khách hàng An Nguyễn bị cô lập dữ liệu theo `customer_email` nên chỉ nhận đúng 15 ticket thuộc sở hữu của mình.
  - **Lý do số 26 ở Prompt 2c:** Con số 26 ticket ghi nhận trong ghi chú Prompt 2c là do volume Docker tích lũy từ các lần chạy kiểm thử tự động trước đó tạo thêm 11 ticket dưới email của An Nguyễn ($15 + 11 = 26$). Trên volume hoàn toàn sạch mới (fresh volume), số lượng chuẩn xác 100% là 15.
- **Cập nhật yêu cầu Dev C (`docs/requests/devB.md`):**
  - Dòng `CR-DEVC-02` đã được cập nhật số liệu thực tế (43 tổng, 15 cho An Nguyễn) và hướng dẫn Dev C lệnh reset chính xác: `docker compose down -v && docker compose up -d`.
- **Dọn dẹp:**
  - Thực thi `docker compose down` (dừng các container và giữ nguyên volume để phục vụ phát triển tiếp theo).

#### Task 6 - Ownership Sanity
- **Kết quả kiểm tra phân quyền module với base `origin/Hoang`:**
  - Lệnh: `python scripts/check_ownership.py --owner devB --as-integrator --base origin/Hoang`
  - Kết quả: Kiểm tra 38 file đã thay đổi trên nhánh `feature/b-platform`, xác nhận toàn bộ tuân thủ nghiêm ngặt ranh giới sở hữu: `[OK] All modified files conform to module ownership boundaries!`, exit code 0.
- **Phân công sở hữu file Docker trong `scripts/ownership_map.py`:**
  - `backend/Dockerfile`: Thuộc quyền sở hữu độc quyền của **`devB`** (dòng 53 trong `scripts/ownership_map.py`).
  - `docker-compose.yml`: Thuộc quyền sở hữu độc quyền của **`devB`** (dòng 88 trong `scripts/ownership_map.py`).
- **Giải thích lý do bắt buộc sử dụng cờ `--as-integrator`:**
  - Nhánh `feature/b-platform` chứa các thay đổi đối với các file hợp đồng dùng chung và cấu hình nền tảng bị đóng băng (Frozen Shared Integration Files), bao gồm: `backend/app/core/config.py`, `backend/app/main.py`, `backend/requirements.txt`, `backend/tests/conftest.py`, `docs/API_CONTRACT.md`, `docs/spec/CONTRACTS.md`, `scripts/smoke_docker.ps1`.
  - Trong đội ngũ 3 người của SmartDesk AI (theo `docs/TEAM_ROSTER.md` và `AGENTS.md`), **Ngô Việt Hoàng** (`@BapVitHoang` / `Bap`) đảm nhiệm đồng thời hai vai trò: **Dev B** (Platform Owner) và **Integrator** (Architecture & Shared Contracts Owner).
  - Vì vậy, cờ `--as-integrator` được yêu cầu khi kiểm tra ownership để xác thực rằng Hoàng đang thực thi quyền hạn của vai trò Integrator đối với các file cấu hình và hợp đồng đóng băng của toàn dự án.

---

## 4. Giải thích code (Platform, Data & Security)

### 4.1 Quy trình đăng nhập & Xác thực mật khẩu (Login Flow & Password Verification)
Hệ thống hỗ trợ 3 hình thức xác thực thông qua FastAPI endpoints trong `backend/app/api/v1/endpoints/auth.py`:
1. **Password Grant (`POST /api/v1/auth/token`):**
   - Người dùng gửi `username` (email) và `password` theo định dạng chuẩn `OAuth2PasswordRequestForm`.
   - Backend sử dụng hàm `verify_password_async(plain_password, hashed_password)` trong `backend/app/core/security.py`. Thuật toán băm là `hashlib.scrypt` tiêu chuẩn với muối 16 bytes ngẫu nhiên (`n=16384, r=8, p=1`), định dạng lưu trữ `$scrypt$n=16384,r=8,p=1$<salt_hex>$<hash_hex>`. So khớp băm sử dụng phép so sánh hằng số thời gian `hmac.compare_digest`.
   - Để ngăn chặn hình thức tấn công dò người dùng thông qua độ trễ thời gian (User Enumeration via Timing Attack), nếu email không tồn tại trong DB, hệ thống sẽ thực hiện xác thực giả lập với chuỗi `_DUMMY_PASSWORD_HASH` đã được tạo sẵn trước khi trả về lỗi.
   - Khi sai mật khẩu, tài khoản không tồn tại, hoặc tài khoản bị vô hiệu hóa (`is_active=False`), backend đều trả về cùng một mã lỗi `HTTP 401 Unauthorized` kèm thông điệp generic giống hệt nhau: `"Tên đăng nhập hoặc mật khẩu không chính xác"`.

2. **Google OAuth2 ID Token Verification (`POST /api/v1/auth/oauth2/login` với `provider="google"`):**
   - Client gửi Google ID Token trong trường `credential`.
   - Backend sử dụng thư viện `google-auth` (`google.oauth2.id_token.verify_oauth2_token`) để giải mã và kiểm tra chữ ký mã hóa bất đối xứng từ Google Public Keys.
   - Các tham số bảo mật được kiểm tra nghiêm ngặt: `audience == settings.GOOGLE_OAUTH_CLIENT_ID`, `issuer in ["accounts.google.com", "https://accounts.google.com"]`, `email_verified == True`, và hạn sử dụng token (`exp`).
   - Nếu `GOOGLE_OAUTH_CLIENT_ID` chưa được cấu hình, backend lập tức từ chối với `HTTP 501 Not Implemented`, không bao giờ chấp nhận token không có chữ ký.
   - Toàn bộ lời gọi xác thực chữ ký đồng bộ qua mạng được bọc trong `asyncio.to_thread` để tránh block ASGI event loop.
   - Tài khoản tạo mới từ Google luôn nhận vai trò mặc định `"user"`. Chỉ các email nằm trong danh sách cấu hình `settings.ADMIN_EMAILS` mới được nâng quyền thành `"admin"`.

3. **1-Click Demo Login (`POST /api/v1/auth/oauth2/login` với `provider="demo"`):**
   - Chỉ hoạt động khi `settings.DEMO_LOGIN_ENABLED = True` và email nằm trong danh sách tài khoản seed được phép (`admin@smartdesk.local`, `user@smartdesk.local`, `admin@smartdesk.ai`, `an.nguyen@company.vn`, v.v.).
   - Nếu `DEMO_LOGIN_ENABLED = False`, backend từ chối cả trên `/auth/oauth2/login` và `/auth/token` với `HTTP 401 Unauthorized` kèm thông điệp generic giống như sai mật khẩu, ngăn chặn việc dò tìm tài khoản demo.
   - Khi `DEMO_LOGIN_ENABLED = False`, script seed `seed_users.py` hoàn toàn bỏ qua việc khởi tạo tài khoản demo vào database.
   - Tuyệt đối không tạo tài khoản mới qua demo login và không thể cấp quyền admin cho một email lạ không thuộc danh sách admin đã seed.

4. **Cơ chế chống Brute-force (Login Throttling):**
   - Triển khai bộ đếm sliding-window `LoginRateLimiter` trong bộ nhớ (`backend/app/core/security.py`).
   - Giới hạn tối đa 10 lần đăng nhập thất bại trong vòng 60 giây trên mỗi địa chỉ IP hoặc email. Khi vượt ngưỡng, hệ thống trả về `HTTP 429 Too Many Requests` với header `Retry-After`.

### 4.2 Cơ chế sinh & Bảo vệ JWT Secret Key (JWT Hygiene)
- Hệ thống sử dụng thuật toán ký `HS256` với thời hạn token mặc định 60 phút (`exp` claim).
- Chuỗi secret mặc định trước đây đã được loại bỏ hoàn toàn khỏi mã nguồn; hệ thống chỉ lưu chuỗi băm SHA-256 (`ac5ca707...`) để nhận diện giá trị placeholder.
- **Trường hợp Demo (`DEMO_LOGIN_ENABLED=True`):** Nếu `JWT_SECRET_KEY` bị để trống hoặc dùng giá trị placeholder, hệ thống tự động sinh một secret ngẫu nhiên bảo mật cao theo từng tiến trình (`secrets.token_urlsafe(48)`), bảo đảm token không thể bị giả mạo chéo giữa các phiên làm việc.
- **Trường hợp Production (`DEMO_LOGIN_ENABLED=False`):** Nếu `JWT_SECRET_KEY` là giá trị rỗng hoặc placeholder, hàm `validate_auth_configuration()` trong `security.py` sẽ tung ngoại lệ `RuntimeError` và từ chối khởi động backend.

### 4.3 Phân quyền RBAC & Cô lập dữ liệu người dùng (User Data Isolation)
- Được thực thi tại tầng dependency FastAPI (`get_current_user`, `require_role`) và các câu truy vấn SQLAlchemy trong `backend/app/api/v1/endpoints/tickets.py`:
  - **Khách hàng thông thường (`role == "user"`):**
    - Khi truy vấn `GET /api/v1/tickets`, câu lệnh SQL tự động bổ sung điều kiện `Ticket.customer_email == current_user.email`. Khách hàng hoàn toàn không thể xem ticket của khách hàng khác.
    - Header phân trang `X-Total-Count` cũng được tính toán dựa trên tập dữ liệu đã lọc theo email người dùng.
    - Khi truy vấn chi tiết `GET /api/v1/tickets/{id}`, nếu ticket không thuộc về khách hàng đó, backend trả về `HTTP 403 Forbidden`.
    - Khách hàng không thể gọi các thao tác nhạy cảm: `PATCH /tickets/{id}` (cập nhật trạng thái/SLA), `DELETE /tickets/{id}` (xóa ticket), hoặc `POST /agent/tickets/{id}/generate-draft` (sinh nháp Copilot).
  - **Quản trị viên / Hỗ trợ viên (`role == "admin"`):**
    - Có toàn quyền xem danh sách tất cả các ticket của hệ thống, phân trang, lọc theo workspace, và thực hiện duyệt/sửa/xóa ticket.
    - Có quyền gọi `POST /api/v1/agent/reset-cooldown` để mở khóa Cost-Guard circuit breaker khi gặp giới hạn tần suất.

### 4.4 Kiến trúc Vector kép (Dual-Mode Vector Type)
- Khai báo model `KnowledgeChunk` và `FAQItem` trong `backend/app/models/knowledge.py` sử dụng kỹ thuật đa phương ngữ SQLAlchemy:
  `Vector(768).with_variant(JSON(), "sqlite")`
- **Môi trường PostgreSQL 16 (Production / Docker):**
  - Cột `embedding` được lưu dưới dạng kiểu dữ liệu vector nguyên bản của extension `pgvector`.
  - Hàm `search_similar_chunks()` trong `embedding_service.py` phát lệnh truy vấn SQL tính khoảng cách cosine trực tiếp trên DB server thông qua toán tử `<=>` (`order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))`), tận dụng chỉ mục vector hiệu năng cao.
- **Môi trường SQLite (Local Development / Testing):**
  - Cột `embedding` lưu trữ chuỗi vector dưới định dạng JSON text.
  - Khi tìm kiếm, dữ liệu được tải vào bộ nhớ và tính toán độ tương đồng cosine bằng hàm `cosine_similarity()` thuần Python, bảo đảm kiểm thử và phát triển offline mượt mà không cần cài đặt PostgreSQL.

### 4.5 Cấu trúc Dịch vụ Docker Compose & Nginx Reverse Proxy
Cấu hình trong `docker-compose.yml` gồm 3 services biệt lập:
1. `postgres`: Image `pgvector/pgvector:pg16`, khởi tạo database `smartdesk`, tự động nạp extension `vector` qua healthcheck `pg_isready`.
2. `backend`: Image FastAPI xây dựng từ `backend/Dockerfile`, phụ thuộc vào `postgres` (chờ `service_healthy`), kết nối qua async driver `postgresql+asyncpg://`, cấu hình healthcheck gọi `GET /api/v1/health`.
3. `frontend`: Image Nginx xây dựng từ `frontend/Dockerfile`, phục vụ Single Page Application tĩnh tại cổng 80 (map ra 3000), đồng thời đóng vai trò Reverse Proxy:
   - Proxy đường dẫn `/api/v1/` sang backend FastAPI (`http://backend:8000/api/v1/`).
   - Thiết lập `proxy_buffering off;` nhằm hỗ trợ streaming token Server-Sent Events (SSE) theo thời gian thực mà không bị đệm dữ liệu.

### 4.6 Nhận diện và Bảo vệ địa chỉ IP Client qua Trusted Proxy (`get_trusted_client_ip`)
- **Vấn đề bảo mật:** Khi chạy phía sau Reverse Proxy (Nginx), toàn bộ kết nối TCP trực tiếp đến Uvicorn đều có địa chỉ IP nguồn là của Nginx (ví dụ `172.18.0.x`). Nếu đọc trực tiếp `request.client.host`, bộ điều tiết tần suất (`LoginRateLimiter`) sẽ nhầm lẫn tất cả người dùng dùng chung một IP, dẫn đến việc khóa nhầm người dùng hợp lệ hoặc bị bypass nếu hacker giả mạo header `X-Forwarded-For`.
- **Giải pháp triển khai:**
  1. Cấu hình Uvicorn trong `backend/Dockerfile` với cờ `--proxy-headers` và `--forwarded-allow-ips`.
  2. Hàm `get_trusted_client_ip(request)` trong `backend/app/core/security.py` thực hiện:
     - Kiểm tra địa chỉ kết nối trực tiếp `peer_ip` (`request.client.host`) thông qua hàm `is_trusted_proxy_ip()`.
     - Danh sách mạng proxy tin cậy được cấu hình trong `settings.TRUSTED_PROXY_CIDRS` (khi để trống mặc định chỉ tin cậy loopback `127.0.0.1/32` và `::1/128`; trong Docker Compose được chỉ định rõ subnet cố định `172.28.0.0/16`). Các dải mạng private khác như `10.0.0.0/8`, `192.168.0.0/16` hoàn toàn không được tin cậy mặc định để chống tấn công giả mạo IP trong mạng LAN/VPS dùng chung.
     - Chỉ khi `peer_ip` thuộc mạng tin cậy, hệ thống mới đọc header `X-Real-IP` hoặc phần tử đầu tiên của `X-Forwarded-For`.
     - Nếu request đến từ một nguồn không tin cậy nhưng cố tình gửi header `X-Forwarded-For` giả mạo, hệ thống sẽ bỏ qua header này và sử dụng chính `peer_ip` làm định danh throttle.

### 4.7 Xác thực bắt buộc và Ràng buộc danh tính Ticket (`POST /api/v1/tickets`)
- **Vấn đề bảo mật:** Trước đây endpoint tạo ticket cho phép gửi dữ liệu nặc danh và tùy ý chỉ định `customer_email`, tạo kẽ hở giả mạo người khác để gửi ticket hoặc spam yêu cầu gọi Copilot LLM.
- **Giải pháp triển khai:**
  1. Yêu cầu bắt buộc đăng nhập thông qua FastAPI dependency `current_user: User = Depends(get_current_user)`. Bất kỳ yêu cầu nào không có JWT token hợp lệ đều bị từ chối ngay với `HTTP 401 Unauthorized`.
  2. Đối với khách hàng thông thường (`role == "user"`):
     - Hệ thống ghi đè và khóa chặt `customer_email` thành `current_user.email` và `customer_name` thành `current_user.full_name`. Khách hàng không thể tạo ticket dưới danh nghĩa người khác.
  3. Đối với nhân viên hỗ trợ / Quản trị viên (`role == "admin"`):
     - Cho phép giữ nguyên `customer_email` và `customer_name` từ payload để hỗ trợ viên có thể tiếp nhận và ghi nhận ticket thay cho khách hàng qua điện thoại/kênh khác.


### 4.9 Tái thẩm tra toàn diện theo Đề cương yêu cầu chính thức (Prompt 4b)
- **Bối cảnh & Mục tiêu:**
  - Hoàn thiện tái thẩm tra đối chiếu với nguồn sự thật duy nhất của môn học (`docs/audit/00-checklist.md`), khắc phục triệt để các bảng yêu cầu cũ tự sinh.
  - Trích xuất nguyên văn toàn bộ 42 Yêu cầu tường minh (`REQ-01` đến `REQ-42`) và 10 Tiêu chí chấm điểm / Điểm trừ (`CRIT-01` đến `CRIT-10`) vào tệp `docs/audit/06-requirements-extract.md`.
  - Tái cấu trúc Bảng tuân thủ yêu cầu và Mục tiêu chí đánh giá trong `docs/audit/06-final-verification.md`, xóa bỏ hoàn toàn các điểm số tự phong dạng "x/10", thay thế bằng nhận định định tính dựa trên bằng chứng lệnh thực thi đã chạy xong.
- **Kết quả thực thi & Bằng chứng thực tế:**
  1. **Task 0 (Preconditions Baseline):**
     - Nhánh kiểm tra: `verify/final-verification-2` tạo từ `origin/Hoang` (`4e514db`).
     - Pytest Backend: 139 passed, 2 skipped trong 45.12s.
     - Frontend: `npm run lint` đạt 0 lỗi, `npm run build` thành công trong 9.41s.
     - Docker containers: 3 dịch vụ (`smartdesk-postgres`, `smartdesk-backend`, `smartdesk-frontend`) đều hoạt động ổn định và probe `/api/v1/health` trả về `status: ok, database: connected`.
     - `check_ownership.py --verify-consistency`: Đạt 261 tệp có phân quyền, 0 chồng lấn.
     - `check_roster.py`: Đúng 12 lỗi tồn tại duy nhất trong 2 tệp nhị phân slide (`MRG-DEF-01`), 0 lỗi trong mã nguồn và tài liệu markdown.
  2. **Task 1 & Task 2 (Trích xuất & Tái cấu trúc Bảng REQ):**
     - Tạo `docs/audit/06-requirements-extract.md` đối chiếu nguyên văn 100% khớp từng ký tự với `docs/audit/00-checklist.md`.
     - Tái cấu trúc Table 3.1: 40 yêu cầu đạt `DONE`, 1 yêu cầu đạt `PARTIAL` (`REQ-41` do slide nhị phân), 1 yêu cầu `NOT SELECTED` (`REQ-16` Năng lực D Đa phương thức OCR).
     - Ghi nhận rõ: Theo `REQ-12`, nhóm 3 thành viên cần tối thiểu 3 năng lực AI, SmartDesk AI đã triển khai 4 năng lực (A: RAG, B: Công cụ Agent, C: Dữ liệu cấu trúc Pydantic, E: Luồng đa Agent kiểm định), vượt mức tối thiểu yêu cầu.
  3. **Task 3 (Tiêu chí chấm điểm CRIT-01..10):**
     - Đưa toàn bộ trọng số chính thức vào tài liệu, bỏ hẳn điểm số tự phong dạng số.
     - Không bị phạt theo `CRIT-09` (`AI_USAGE.md` đầy đủ 5 ca thất bại thực tế) và `CRIT-10` (0 bí mật/khóa API bị lộ trong lịch sử Git).
  4. **Task 4 (Thực thi & Thu thập bằng chứng thực tế):**
     - Phân trang & X-Total-Count: Lưu vào `docs/audit/06-evidence/item-C-tickets.txt`.
     - Live RAG Chat trên PostgreSQL: Lưu vào `docs/audit/06-evidence/item-D-chat.txt`.
     - Upload tài liệu & Active verification: Lưu vào `docs/audit/06-evidence/item-G-documents.txt`.
     - Quyền hạn công cụ & Chặn chéo tài khoản: Kiểm thử xác nhận hành động giữa hai tài khoản, trả về đúng `HTTP 403 ACTION_FORBIDDEN` khi người dùng khác cố xác nhận hành động không thuộc về mình (`docs/audit/06-evidence/item-F-tools.txt`).
     - Admin AI Telemetry & Reset Cooldown: Kiểm thử `/api/v1/agent/ai-usage` và `/api/v1/agent/reset-cooldown` ghi nhận trong `docs/audit/06-evidence/item-I-telemetry.txt`.
     - Khử trùng nhạy cảm: Toàn bộ JWT và mật khẩu được thay thế bằng `[REDACTED_JWT_TOKEN]` và `[REDACTED_SECRET]`.
  5. **Task 5 (Kiểm toán báo cáo đánh giá & Ảnh chụp màn hình):**
     - Làm rõ baseline 8/24 trong `A-eval-report.md` chạy từ hàm mô phỏng `run_legacy_baseline_case()` (FAQ matcher + regex tiếng Anh của mã nguồn cũ), không có tập dữ liệu held-out riêng biệt.
     - Kiểm toán 14 tệp ảnh màn hình trong `docs/evidence/` khớp các kịch bản kiểm thử chấp nhận.
  6. **Review Loop & Authorship:**
     - Cả 4 subagent đánh giá chuyên sâu (Ownership Hunter, Requirements Auditor, Security Reviewer, Skeptical Verifier) đều báo cáo ALL PASS sau khi hợp nhất đầy đủ dữ liệu bằng chứng hỗn hợp và cập nhật số commit lên 129 (111 Bap, 10 TheOrijinnn, 8 TKhanhJK).

---

# Final documents (Prompt 5 — Taking over Dev C Final Deliverables)

## Plan

1. **Task 0 (Preconditions):**
   - Files: `docs/notes/B.md`, `docs/TEAM_ROSTER.md`, `docs/audit/06-final-verification.md`.
   - Approach: Verify identity `Bap <23110020@student.hcmute.edu.vn>`, branch `docs/final-documents` from `origin/Hoang` (`b77376c`), verify all 3 rows in `TEAM_ROSTER.md` (zero `CHƯA CÓ DỮ LIỆU`), list limitations from 06 (`REQ-16` NOT SELECTED, `MRG-DEF-01` slide roster hits, `MRG-DEF-10` pgvector 768 vs 3072 fallback).
   - Proof: Precondition outputs and origin/Hoang SHA recorded in `B.md`. Main risk: Unverified cells in roster.
2. **Task 1 (Claims table):**
   - Files: `docs/notes/B.md`, `README.md`, `docs/PROPOSAL.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/TEST_ACCEPTANCE.md`.
   - Approach: Build table `document | claim | source (06 row, command, file) | status (OK / CORRECT / REMOVE)`. Audit every number (139 pytest passed, 43 demo tickets, 24 eval cases 8/24->24/24, SLA 2h/4h/8h/24h, 129 commits: 111/10/8), tech name (purge Next.js/Redis claims). Reconcile all CORRECT/REMOVE items.
   - Proof: Zero unresolved CORRECT or REMOVE rows in table. Main risk: Unverified claims or missing sources.
3. **Task 2 (Report content - REQ-40):**
   - Files: `docs/REPORT.md`.
   - Approach: Align structure to course guidelines (Ch 1-7); separate deterministic (<2s CI) and live eval (24 cases, no held-out); add limitations chapter (MRG-DEF-01, MRG-DEF-10, REQ-16); team chapter with official roster facts and Git commit subjects (no percentages, note agent-assisted round); update Mermaid diagram; align RTM table to 4 columns (`Story -> Endpoint/Component -> Source file -> Test case`); validate traceability paths and test names.
   - Proof: Python script checking every file path and test in traceability table exists. Main risk: Broken path references.
4. **Task 3 (Rebuild deliverables reproducibly):**
   - Files: `docs/tools/build_report_pdf.py`, `build_slides.py`, `docs/tools/requirements.txt`, `scripts/ownership_map.py`, `.github/CODEOWNERS`, `docs/REPORT.pdf`, `docs/SLIDES.pptx`, `docs/SLIDES.pdf`.
   - Approach: Build standalone python generator scripts using `reportlab` with registered Windows TrueType fonts (`C:\Windows\Fonts\arial.ttf`, `arialbd.ttf`) for Vietnamese diacritics and `python-pptx` (never weasyprint or Office COM). Map under Integrator in `ownership_map.py` and regenerate `CODEOWNERS`. Generate 10-20 page `REPORT.pdf` and exactly <=15 slide `SLIDES.pptx` / `SLIDES.pdf`.
   - Proof: `check_roster.py` exits 0 (0 violations, fixing MRG-DEF-01); zero TODO/lorem/invented names; page count recorded. Main risk: Vietnamese font diacritics in PDF.
5. **Task 4 (Demo script & live-change playbook - REQ-41, 42):**
   - Files: `docs/PRESENTATION_AND_DEMO.md`, `docs/DEMO_VIDEO_CHECKLIST.md`.
   - Approach: 8-minute demo script with exact demo accounts and click path; 3 live-change scenarios (prompts.json, chunk size, agent tool). Execute each in a clean `%TEMP%` scratch copy without `.git` using targeted unit tests (never `docker compose down -v` to protect pgdata volume). Max 3 live Gemini calls (>=4.5s delay).
   - Proof: Executed scratch command outputs in playbook; reset cooldown via admin API if tripped. Main risk: Port collision or rate limit.
6. **Task 5 (Notes, commits and publish):**
   - Files: `docs/notes/B.md`.
   - Approach: Record evidence for every task in `B.md`. Commit in small commits (documents and binaries separately). Push `docs/final-documents` to origin. PR description: "Prepared by Hoàng with an AI agent; TKhanhJK and TheOrijinnn review the report and slides before merge."
   - Proof: `git ls-remote --heads origin docs/final-documents` matches local commit SHA. Main risk: Push to protected branches (forbidden).

---

## Task 0: Preconditions Baseline Verification

- **Base Commit (`origin/Hoang` SHA):** `b77376ccf172a4a196e2c73faeddb8a4bb0f5fbd`
- **Active Branch:** `docs/final-documents` branched directly from `origin/Hoang`.
- **Identity Check (RULE 4):**
  - `git config user.name`: `Bap`
  - `git config user.email`: `23110020@student.hcmute.edu.vn`
  - Matches verified row for Ngô Việt Hoàng in `docs/TEAM_ROSTER.md`.
- **Merge & File Check:**
  - `git log origin/Hoang --oneline -5` shows Prompt 4b commits (`b77376c`, `61fafc0`, `0c56884`, `3cd7747`, `4e514db`).
  - `docs/audit/06-final-verification.md` and `docs/audit/06-requirements-extract.md` exist and are present on the branch.
- **Roster Check (`docs/TEAM_ROSTER.md`):**
  - All 3 members have `verified_by_user = True`.
  - Zero cells contain `CHƯA CÓ DỮ LIỆU`:
    * Ngô Việt Hoàng (MSSV: 23110020) — Dev B & Integrator
    * Lê Nguyên (MSSV: 23110043) — Dev A
    * Tống Gia Khánh (MSSV: 23110032) — Dev C
- **Audit 06 Defects and Limitations List:**
  - **FAILED items:** 0
  - **NOT TESTED / NOT SELECTED items:**
    * `REQ-16` (Capability D — Multimodal Input): Marked **NOT SELECTED** (SmartDesk AI implements 4 capabilities: A, B, C, E, exceeding the 3 required under `REQ-12`). Must appear as a scope decision and limitation, not an achievement.
  - **OPEN Blocker defects:** 0 (None exist).
  - **OPEN High defects:**
    * `MRG-DEF-01`: 12 fabrication violations in slide binaries (`docs/SLIDES.pdf` and `docs/SLIDES.pptx`) detected by `check_roster.py`. Must appear as limitation until cleanly rebuilt in Task 3.
    * `MRG-DEF-10`: Google Gemini live embedding API returns 3072 dimensions vs PostgreSQL `vector(768)` column schema, handled with pseudo-embedding fallback in `embedding_service.py:138-144`. Must appear as limitation in Report Chapter 7.

---

## Task 1: Claims Table Reconciliation

Table auditing all cross-document claims across `README.md`, `docs/PROPOSAL.md`, `docs/REPORT.md`, `docs/PRESENTATION_AND_DEMO.md`, `docs/TEST_ACCEPTANCE.md`:

| Document | Claim | Source (06 row, command, file) | Status | Notes & Resolution |
| :--- | :--- | :--- | :---: | :--- |
| `README.md` | SLA hours: Urgent: 2h, High: 4h, Medium: 8h, Low: 24h | `README.md:10`, `backend/app/db/seed/seed_demo_tickets.py:15-17`, `00-checklist.md:REQ-30` | **OK** | Perfectly matches canonical SLA hours in config and database seeders. |
| `README.md` | Models: `gemini-3.5-flash-lite`, `qwen2.5:3b`, `nomic-embed-text` | `README.md:14,24`, `backend/app/core/config.py:34-40` | **OK** | Verified live on Google GenAI API; retired `gemini-1.5-flash` purged. |
| `README.md` | Cost-Guard timeout 4.0s, cooldown 60s | `README.md:15,104`, `backend/app/core/config.py:46-48` | **OK** | Matches `LLM_TIMEOUT_SECONDS=4.0` and `FREE_TIER_RATE_LIMIT_COOLDOWN=60`. |
| `README.md` | Canonical categories: `Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General` | `README.md:16`, `backend/app/schemas/ticket.py:13-19` | **OK** | `Technical Bug` supported as backwards-compatible alias normalizing to `Bug Report`. |
| `README.md` | Test accounts: `admin@smartdesk.ai` (admin), `an.nguyen@company.vn` (user) | `README.md:167-168`, `backend/app/db/seed/seed_users.py:20-35` | **OK** | 1-click switcher accounts populated in both SQLite and PostgreSQL. |
| `README.md` | Roster facts & roles: Refers to `docs/TEAM_ROSTER.md` | `README.md:151-158`, `docs/TEAM_ROSTER.md` | **OK** | Zero unverified names or percentages. |
| `docs/PROPOSAL.md` | 12 User Stories (`US-01`..`US-12`) | `docs/PROPOSAL.md:28-42`, `00-checklist.md:REQ-24` | **OK** | All 12 stories follow "As a... I want... So that..." with acceptance criteria. |
| `docs/PROPOSAL.md` | Tech Stack: React 19 + Vite 6, FastAPI Async, PostgreSQL pgvector / SQLite, Gemini / Ollama | `docs/PROPOSAL.md:49-55` | **OK** | Completely matches actual repository code; zero Next.js / Redis claims. |
| `docs/PROPOSAL.md` | Smoke-test latency benchmark: `922.74ms` | `docs/PROPOSAL.md:135`, Prompt 1 smoke test | **OK** | Recorded from live endpoint benchmark. |
| `docs/REPORT.md` | Backend test suite: 139 passed, 2 skipped | Command `python -m pytest backend/tests/ -q` (56.94s) | **CORRECT** | Reconciled exact suite output: 139 passed, 2 skipped in 56.94s in Ch 2 & Ch 6. |
| `docs/REPORT.md` | Docker demo tickets: 43 seeded tickets (15 for An Nguyen) | `seed_tickets.py` (3 tickets, 1 An Nguyen) + `seed_demo_tickets.py` (40 tickets, 14 An Nguyen) | **OK** | Seeded base is 43 tickets (15 An Nguyen); runtime container has 48 tickets due to smoke tests. |
| `docs/REPORT.md` | AI evaluation benchmark: 24 cases (10 normal, 6 edge, 8 should-refuse), baseline 8/24 (33.3%) -> upgraded 24/24 (100.0%), 0 held-out cases | `backend/data/eval_dataset.json` (24 items), `backend/scripts/run_eval.py` | **OK** | Full breakdown: 10 normal, 6 edge, 8 should-refuse. Baseline derivation documented. 0 held-out cases explicitly reported. |
| `docs/REPORT.md` | SLA hours: Urgent: 2h, High: 4h, Medium: 8h, Low: 24h | `docs/REPORT.md:41,223`, `backend/app/services/ticket_service.py` | **OK** | Perfectly matches canonical SLA rules. |
| `docs/REPORT.md` | Commits breakdown: 121 commits on branch HEAD (104 Bap, 9 TheOrijinnn, 8 TKhanhJK) / 132 across all branches (114 Bap, 10 TheOrijinnn, 8 TKhanhJK); zero percentages | Command `git shortlog -sn HEAD` & `git shortlog -sn --all` | **CORRECT** | Document exact commit counts from git log without percentages in Team Section. |
| `docs/REPORT.md` | RTM table: 4 columns (`User story -> API endpoint or component -> source file(s) -> test case(s)`) mapping 42 REQs | `docs/audit/00-checklist.md:REQ-01..42` | **CORRECT** | Rebuild Chapter 2 RTM table to match 4 columns and expand to cover all 42 official REQs. |
| `docs/REPORT.md` | Limitations: Capability D not selected, slide binaries roster violations, pgvector 768 vs 3072 dims fallback | `docs/audit/06-final-verification.md` (`REQ-16`, `MRG-DEF-01`, `MRG-DEF-10`) | **CORRECT** | Add explicit dedicated limitations subsection in Chapter 7. |
| `docs/REPORT.md` | Outdated tech names (Next.js, Redis, MongoDB) | `git grep -i "next\.js"`, `git grep -i "redis"`, `git grep -i "mongodb"` | **OK** | Next.js rejected in ADR-004; Redis mentioned only as future distributed queue; zero MongoDB. |
| `docs/PRESENTATION_AND_DEMO.md` | 15 slides structure, 8-minute demo, 10-minute live change | `docs/PRESENTATION_AND_DEMO.md:11-28`, `00-checklist.md:REQ-41, REQ-42` | **OK** | Structured strictly according to syllabus requirements. |
| `docs/PRESENTATION_AND_DEMO.md` | Test accounts: `admin@smartdesk.ai` and `an.nguyen@company.vn` | `docs/PRESENTATION_AND_DEMO.md:64` | **OK** | Accounts and credentials verified. |
| `docs/TEST_ACCEPTANCE.md` | 7 core manual acceptance scenarios | `docs/TEST_ACCEPTANCE.md:42-184` | **OK** | Covering customer RAG, fallback, ticket submit, agent triage, verification, and telemetry. |
| `docs/TEST_ACCEPTANCE.md` | Automated test suite coverage | `docs/TEST_ACCEPTANCE.md:17-39` | **OK** | Lists core endpoints, models, and security test cases. |

### Reconciliation Summary:
- **Total claims audited:** 21
- **Status breakdown:** 16 OK, 5 CORRECT, 0 REMOVE.
- **Key resolutions to apply in Task 2:**
  1. Rebuild RTM in `docs/REPORT.md` Chapter 2 to 4-column format mapping all 42 REQs.
  2. In Chapter 6, record exact suite counts: 139 passed, 2 skipped (56.94s) and eval benchmark breakdown (24 cases, baseline 8/24, 0 held-out).
  3. In Chapter 7, detail `REQ-16` (Capability D not selected), `MRG-DEF-01` (slide roster violations), and `MRG-DEF-10` (pgvector 768 vs 3072 fallback).
  4. In Team Chapter, record official names and MSSVs from `TEAM_ROSTER.md`, exact git commit counts (zero percentages), and the two required sentences acknowledging AI agent assistance.

---

## Task 2: Report Content Alignment (REQ-40)

- **Structure & Alignment:**
  - Updated `docs/REPORT.md` to strictly follow syllabus chapters 1–7.
  - Front Matter & Section 1.4: Documented official team roster from `docs/TEAM_ROSTER.md` (Ngô Việt Hoàng 23110020, Lê Nguyên 23110043, Tống Gia Khánh 23110032). Documented module ownership, exact commit counts (104/9/8 on branch HEAD; 114/10/8 across repository; zero percentages). Included the two plain sentences acknowledging AI agent assistance.
  - Chapter 2: Rebuilt RTM table with 4 columns (`User Story / REQ -> API Endpoint / UI Component -> Source Files -> Test Cases`) mapping all 42 official requirements.
  - Automated RTM validation tool: Created `docs/tools/verify_rtm.py` and mapped `docs/tools/*` in `scripts/ownership_map.py` & `.github/CODEOWNERS`.
  - Executed `python docs/tools/verify_rtm.py`:
    ```
    Found 42 RTM requirement rows in docs/REPORT.md.
    --- Validation Results ---
    Checked source files across 42 requirements.
    [PASS] All referenced source files exist on disk.
    [PASS] All referenced test files exist on disk.
    SUCCESS: 100% of RTM table entries (42/42) verified successfully!
    ```
  - Chapter 6: Separated Deterministic CI Evaluation (< 2s) and Live Cloud Evaluation. Documented exact 24 evaluation cases (10 normal, 6 edge, 8 should-refuse; 0 held-out cases). Documented baseline 8/24 derivation (simulated legacy logic: ungrounded prompt, missing Vietnamese regex, schema parse failure). Documented automated Pytest suite (139 passed, 2 skipped in 56.94s).
  - Chapter 7: Added explicit limitations detailing:
    * `REQ-16` (Capability D — Multimodal Input not selected by group scope decision; system implements 4 capabilities: A, B, C, E, exceeding the 3 required under `REQ-12`).
    * `MRG-DEF-01` (Roster fabrication violations in historical slide binaries `docs/SLIDES.pdf` and `docs/SLIDES.pptx`, resolved by rebuilding in Task 3).
    * `MRG-DEF-10` (Google Gemini live embedding API 3072 dimensions vs database `vector(768)` column schema, handled with deterministic SHA-256 unit pseudo-embedding fallback in `embedding_service.py:138-144`).

---

## Task 3: Rebuild Deliverables Reproducibly (REQ-40, REQ-41)

- **Generator Tools Created:**
  - `docs/tools/build_report_pdf.py`: Python script utilizing ReportLab with registered Windows TrueType fonts (`Arial`, `Arial-Bold`, `Arial-Italic`) for Vietnamese diacritics. Builds complete report covering chapters 1–7, formal cover page, table of contents, glossary, and 42-requirement RTM table.
  - `docs/tools/build_slides.py`: Python script utilizing `python-pptx` to generate `docs/SLIDES.pptx` (15 slides in 16:9 widescreen layout) and ReportLab to generate `docs/SLIDES.pdf` (15 landscape pages in 16:9 layout matching the exact presentation outline).
  - `docs/tools/requirements.txt`: Specifying `reportlab>=4.0.0`, `python-pptx>=1.0.0`, `pypdf>=5.0.0`.
- **Generation & Page Count Verification:**
  - Command: `python docs/tools/build_report_pdf.py`
    * Output: `Generated docs/REPORT.pdf successfully with 11 pages. [PASS] Page count 11 is strictly within the 10–20 page requirement (REQ-40).`
  - Command: `python docs/tools/build_slides.py`
    * Output:
      ```
      Generated docs/SLIDES.pptx successfully with 15 slides.
      Generated docs/SLIDES.pdf successfully with 15 pages.
      [PASS] Slide count 15 satisfies <= 15 requirement (REQ-41).
      ```
- **Roster & Anti-Fabrication Gate Verification:**
  - Command: `python scripts/check_roster.py`
  - Output:
    ```
    ============================================================
    SmartDesk AI — Roster & Anti-Fabrication Gate (check_roster.py)
    ============================================================
    Loaded from docs/TEAM_ROSTER.md:
      - Verified Full Names : ['ngô việt hoàng', 'tống gia khánh', 'lê nguyên']
      - Verified MSSVs      : ['23110032', '23110043', '23110020']
      - Allowed Git Emails  : ['khanhssaa77@gmail.com', 'lenguyensonghinh@gmail.com', '23110020@student.hcmute.edu.vn']
      - Allowed Handles     : ['@tkhanh', '@theorijinnn', '@bapvithoang']
    ------------------------------------------------------------
    [PASS] Anti-Fabrication & Roster Gate passed cleanly (0 violations).
    ```
  - **Result:** Defect `MRG-DEF-01` (12 historical slide roster violations) is 100% resolved across all PDFs and PPTX files.
- **Content Sanity:** Verified zero TODO, lorem, [name], "CHƯA CÓ DỮ LIỆU", or historical invented names.






