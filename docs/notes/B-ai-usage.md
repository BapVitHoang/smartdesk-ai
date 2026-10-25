# Developer B — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.
> **Rule:** Record every real AI mistake you find, with the commit hash; never invent one.

---

### Session 1: OAuth2 Authentication, HS256 JWT & RBAC Data Isolation (`TASK-12`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Hoàn thiện Task B1: Xác thực OAuth2 + HS256 JWT, Phân quyền RBAC (admin/user) & Cô lập dữ liệu trong auth.py, deps.py, tickets.py và agent.py."
- **Manual Verification & Changes:**
  - Manually verified PyJWT HS256 token generation and backward-compatibility with `demo_jwt_token_for_{email}`.
  - Verified customer ticket filtering: customer `an.nguyen@company.vn` only sees their own tickets.
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue:* When testing `admin_client` and `user_client` together in `test_rbac_ticket_isolation_and_admin_only_routes`, the two pytest fixtures conflicted on `app.dependency_overrides[get_current_user]`. The `user_client` fixture ran second and clobbered the override, causing the subsequent admin DELETE call to run with user permissions and fail with 403.
  - *File:* `backend/tests/test_auth_module.py`
  - *Fix Applied:* Switched test to generate real HS256 JWTs via `/api/v1/auth/oauth2/login` and dispatched them via explicit `Authorization: Bearer <token>` headers using `unauth_client`, ensuring true end-to-end token validation without dependency override collisions.

---

### Session 2: Server-side Sorting, Pagination Header & Workspace Deletion (`TASK-13`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Bổ sung DELETE, Server-Side Sorting, Pagination Header X-Total-Count & Kết nối Copilot trong ticket_service.py, tickets.py, workspaces.py."
- **Manual Verification & Changes:**
  - Verified `sort_by` (`priority`, `status`, `sla_hours`, `created_at`) and `sort_order` (`asc`, `desc`).
  - Verified `DELETE /api/v1/workspaces/1` returns `HTTP 400 Bad Request` while custom workspaces return `HTTP 204 No Content`.
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue:* The initial count query `select(func.count(Ticket.id))` did not apply the same customer email or filter clauses as the main query, which would cause customer requests to return the total ticket count of the whole database in `X-Total-Count` instead of their filtered count.
  - *File:* `backend/app/api/v1/endpoints/tickets.py`
  - *Fix Applied:* Replicated all active where clauses (RBAC user filter, workspace filter, status, category, priority, and text search) into `count_query`.

---

### Session 3: Dual-Dialect pgvector and PII Masking on Embeddings (`TASK-14`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Kích hoạt Dual-Dialect pgvector trên PostgreSQL trong knowledge.py, session.py, embedding_service.py và hoàn thiện test platform."
- **Manual Verification & Changes:**
  - Verified `Vector(768).with_variant(JSON(), "sqlite")` compatibility across SQLite and PostgreSQL.
  - Verified `redact_pii()` mask is applied before embedding API calls.
  - Verified `docker compose config` parses without syntax errors.

---

### Session 4: Security Hardening — Password Hashing, Google ID Token Verification & Brute-force Throttle (`REQ-06`, `REQ-09`, `REQ-36`)
- **Date:** 2026-10-23
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Khắc phục triệt để lỗ hổng xác thực: kiểm tra mật khẩu bằng salted scrypt, xác thực chữ ký Google ID token qua google-auth, chặn đăng nhập tài khoản ảo và bổ sung sliding-window throttle chống brute-force."
- **Manual Verification & Changes:**
  - Verified `hash_password()` and `verify_password_async()` using standard library `hashlib.scrypt` with constant-time compare (`hmac.compare_digest`).
  - Verified `_DUMMY_PASSWORD_HASH` execution to ensure identical response latency for non-existent users, preventing username enumeration.
  - Verified Google ID token validation using `google.oauth2.id_token.verify_oauth2_token` with audience check, returning HTTP 501 when unconfigured and rejecting forged/unsigned tokens with HTTP 401.
  - Verified 1-click Demo login is locked to `DEMO_ACCOUNT_EMAILS` and returns HTTP 403 when `DEMO_LOGIN_ENABLED=false`.
  - Added sliding-window in-memory throttle returning HTTP 429 after 10 failed attempts per email / client IP.
  - Created 11 dedicated offline security test cases in `backend/tests/platform/test_auth_security.py` (all PASS).
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue:* Initial draft implementation in `auth.py` did not check `is_active` status on existing users during Google OAuth2 login and demo login, which would allow deactivated accounts to continue logging in if they authenticated via external provider.
  - *File:* `backend/app/api/v1/endpoints/auth.py`
  - *Fix Applied:* Enforced explicit `user.is_active` check across all authentication branches (`_demo_login`, `_google_login`, and `login_for_access_token`), raising uniform 401/403 errors for deactivated users.

---

### Session 5: JWT Dynamic Secret Hardening, Dependency Audit, Docker Smoke Script & Reset-Cooldown Alias
- **Date:** 2026-10-25
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Thực hiện các tác vụ platform cho Dev B và Integrator: Không bao giờ dùng default JWT secret trong code; Kiểm định dependency truth qua clean venv và AST scan; Thêm scripts/smoke_docker.ps1 cho Docker/pgvector; Thêm route POST /agent/reset-cooldown; Kiểm tra cô lập REQ-08."
- **Manual Verification & Changes:**
  - Verified SHA-256 detection of known placeholder JWT secrets, generating ephemeral per-process secrets when `DEMO_LOGIN_ENABLED=true` and refusing startup when disabled.
  - Verified clean venv installation (`sd-venv-clean`) with `pip install -q -r backend/requirements.txt` and AST scan across all backend code (all 20 dependencies verified necessary).
  - Verified syntax of `scripts/smoke_docker.ps1` via PowerShell AST parser and verified blocker detection when Docker daemon is offline.
  - Verified `POST /api/v1/agent/reset-cooldown` and its alias `POST /api/v1/agent/ai-usage/reset-cooldown` with 4 platform tests.
  - Verified REQ-08: Grep of `frontend/package.json`, `frontend/src/`, and `frontend/dist/` confirmed 0 client-side Google SDKs or API keys.
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue 1:* In `backend/tests/platform/test_agent_reset_cooldown.py`, the AI assumed `llm_service._cooldown_until` was a `datetime` object (`datetime.now(timezone.utc) + timedelta(...)`), causing `AssertionError: assert False is True`. Inspection of `backend/app/services/llm_service.py` revealed that `cooldown_until` is a `time.time()` float timestamp.
  - *Commit Subject:* `feat(agent): expose reset-cooldown on agent router and ignore eval runs`
  - *Fix Applied:* Updated test to assign `llm_service.cooldown_until = time.time() + 60.0`, resulting in 4/4 passing tests.
  - *Observed Issue 2:* In `scripts/ownership_map.py`, newly introduced integrator-managed paths (`scripts/smoke_docker.ps1` and `backend/data/eval_runs/.gitignore`) were not listed in the explicit integrator mapping, causing `check_ownership.py` to flag a cross-owner violation.
  - *Commit Subject:* `chore(docker): add smoke_docker.ps1 script and record daemon blocker`
  - *Fix Applied:* Added both paths to `integrator` in `scripts/ownership_map.py` and regenerated `.github/CODEOWNERS` via `scripts/gen_codeowners.py`.


