# SmartDesk AI — Integration Merge Report (`07-merge-report.md`)

**Branch:** `integration/merge-all` (branched from `origin/Hoang` at `9fc5443bf0d153b4ecbe4be8bfe48d5856fd1b26`)  
**Worktree:** `D:\SPKT_2023\year_4\newtech\smartdesk-merge`  
**Integrator:** `@BapVitHoang` (`Bap <23110020@student.hcmute.edu.vn>`) — Dev B & Integrator  
**Date:** 2026-10-25  

---

## Plan

### Phase 1 Integration Plan (Reviewed by Scope Guard & Plan Skeptic)
1. **Task 0 (Setup & Safety Net):**
   - Verify main workspace (`D:\SPKT_2023\year_4\newtech\smartdesk-ai`) is clean on `Hoang`.
   - Run `git fetch --all --prune`, record the SHA, author, email, and subject of every `origin/*` branch, and verify git identity (`Bap <23110020@student.hcmute.edu.vn>`) against `docs/TEAM_ROSTER.md`.
   - Create local safety backup branches (`backup/merge-*`) for `Hoang`, `feature/b-platform`, `feature/a-ai-engine`, `feature/c-frontend-docs`, `Nguyen2`, `TKhanh`, and `Nguyen`.
   - Create isolated worktree `..\smartdesk-merge` on branch `integration/merge-all` from `origin/Hoang` and create git-ignored `backend/.env` from `backend/.env.example` with empty `GEMINI_API_KEY`.
2. **Task 1 (Inventory — Read-Only):**
   - Compute pairwise ancestry (`git merge-base --is-ancestor`), commit log, file diff, ownership classification (`scripts/ownership_map.py`), and secret/forbidden-artifact scan across all candidate branches.
   - Determine the minimal active merge set (`origin/feature/b-platform`, `origin/Nguyen2`, `origin/feature/c-frontend-docs`, `origin/TKhanh`), excluding obsolete pre-restructure `origin/Nguyen` (`56c9496`, 2026-09-22) and superseded `origin/feature/a-ai-engine` (`cb404fe`, ancestor of `origin/Nguyen2`).
   - Save full inventory output to `docs/audit/07-evidence/task1-inventory.txt`.
3. **Task 2 (Merge Dev B — `origin/feature/b-platform`):**
   - Merge `origin/feature/b-platform` with `git merge --no-ff`.
   - Enforce Policy **P8** on `AI_USAGE.md` (preserve `origin/Hoang`'s version; save `feature/b-platform`'s addition as a proposal patch in `docs/audit/07-alternatives/AI_USAGE-b-platform.patch`).
   - Run `pytest`, `check_roster.py`, and `check_ownership.py --verify-consistency`; save outputs to `docs/audit/07-evidence/task2-checks.txt`.
4. **Task 3 (Merge Dev A — `origin/Nguyen2`):**
   - Merge `origin/Nguyen2` with `git merge --no-ff`.
   - Run offline `pytest`, `run_eval.py --mode deterministic`, `check_roster.py`, and `check_ownership.py --verify-consistency`; save outputs to `docs/audit/07-evidence/task3-checks.txt`.
   - Audit Dev A interfaces against `docs/spec/CONTRACTS.md` and record differences as defects without modifying Dev A code.
5. **Task 4 (Merge Dev C — `origin/feature/c-frontend-docs` then `origin/TKhanh`):**
   - Merge `origin/feature/c-frontend-docs` first (`--no-ff`), resolving `docs/requests/devC.md` per **P6** (union of `CR-001` and `CR-002`) and taking binary deliverables (`docs/REPORT.pdf`, `docs/SLIDES.pdf`, `docs/SLIDES.pptx`, `docs/evidence/*.png`) per **P5**; run frontend + backend checks (`docs/audit/07-evidence/task4a-checks.txt`).
   - Merge `origin/TKhanh` second (`--no-ff`), resolving `docs/notes/C-ai-usage.md` per **P6** (keeping both the 2026-10-22 Session 5 and 2026-10-25 Session 6 entries); run frontend + backend checks (`docs/audit/07-evidence/task4b-checks.txt`).
   - Audit Dev C frontend API services (`frontend/src/services/api/*.ts`) against `docs/spec/CONTRACTS.md` and `docs/API_CONTRACT.md`.
6. **Task 5 (Repair Merge-Induced Breakage Only):**
   - Distinguish merge-induced failures from pre-existing source-branch defects; record analysis in `docs/audit/07-evidence/task5-repairs.txt`.
7. **Task 6 (Whole-Stack Verification — No Live LLM):**
   - Run `scripts/verify_setup.ps1` (`docs/audit/07-evidence/task6-verify-setup.txt`), `docker compose build` + `scripts/smoke_docker.ps1` + `docker compose down` (`docs/audit/07-evidence/task6-docker-smoke.txt`), and regenerate `.github/CODEOWNERS` via `scripts/gen_codeowners.py`.
8. **Task 7 & Phase 3 & Task 8:**
   - Compile `docs/audit/07-merge-report.md` and `docs/requests/devB.md`, run 4-subagent Self-Review Loop, and push `origin integration/merge-all`.

---

## 1. Branch SHA Table and Ancestry Matrix

### 1.1 Remote Branch SHA Table (Recorded at Task 0 after `git fetch --all --prune`)

| Remote Branch | Tip Commit SHA | Commit Date (ISO) | Author Name & Email | Commit Subject |
| :--- | :--- | :--- | :--- | :--- |
| `origin/Hoang` | `9fc5443bf0d153b4ecbe4be8bfe48d5856fd1b26` | `2026-10-23 10:29:06 +0700` | `Bap <23110020@student.hcmute.edu.vn>` | `Update TEAM_ROSTER.md` |
| `origin/feature/b-platform` | `5415245ecf12eabb34620505b5596ec64804c44d` | `2026-10-25 09:16:05 +0700` | `Bap <23110020@student.hcmute.edu.vn>` | `docs(review): log self-review round 1 for prompt 2d and record out-of-scope requests` |
| `origin/feature/a-ai-engine` | `cb404fecb89874bcc74be0954ebea933f671215b` | `2026-10-23 05:27:52 +0700` | `Bap <23110020@student.hcmute.edu.vn>` | `fix(ai-engine): resolve Gemini 3.5 400 INVALID_ARGUMENT, add circuit breaker error classification, and verify audit gaps` |
| `origin/Nguyen2` | `62c7e5a69bdda626cc57211f8c16b27cc155d45f` | `2026-10-24 20:14:26 +0700` | `TheOrijinnn <lenguyensonghinh@gmail.com>` | `Merge remote-tracking branch 'origin/feature/a-ai-engine' into Nguyen2` |
| `origin/feature/c-frontend-docs` | `74d3319671847f93129f5ef7c85a5ab403319f1d` | `2026-10-23 05:21:30 +0700` | `Bap <23110020@student.hcmute.edu.vn>` | `feat(c-qa-docs): add offline cross-feature tests, visual verification evidence, capstone report PDF, and presentation slides` |
| `origin/TKhanh` | `44a785937f41f2a73d6028392f8da9c8eb469328` | `2026-10-25 17:51:38 +0700` | `TKhanhJK <khanhssaa77@gmail.com>` | `feat(ux): support authenticated ticket creation and 43 demo tickets pagination (CR-DEVC-01, CR-DEVC-02)` |
| `origin/Nguyen` | `56c9496b0760f8f2f58a9e58b29d5ce7aac209a8` | `2026-09-22 13:16:10 +0700` | `TheOrijinnn <lenguyensonghinh@gmail.com>` | `FIx header UI` |
| `origin/master` | `4b15b530a65751c387d4b5297627950a4e7030f1` | `2026-09-17 07:27:14 +0700` | `Bap <23110020@student.hcmute.edu.vn>` | `thêm rules` |

### 1.2 Pairwise Ancestry Matrix (`git merge-base --is-ancestor <Row> <Column>`)

| Row is Ancestor of Column? | `Hoang` | `b-platform` | `a-ai-engine` | `c-frontend-docs` | `Nguyen2` | `TKhanh` | `Nguyen` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`origin/Hoang`** (`9fc5443`) | - | **YES** | no | no | **YES** | no | no |
| **`origin/feature/b-platform`** (`5415245`) | no | - | no | no | no | no | no |
| **`origin/feature/a-ai-engine`** (`cb404fe`) | no | no | - | no | **YES** | no | no |
| **`origin/feature/c-frontend-docs`** (`74d3319`) | no | no | no | - | no | no | no |
| **`origin/Nguyen2`** (`62c7e5a`) | no | no | no | no | - | no | no |
| **`origin/TKhanh`** (`44a7859`) | no | no | no | no | no | - | no |
| **`origin/Nguyen`** (`56c9496`) | no | no | no | no | no | no | - |

### 1.3 Merge Set Selection Rationale
1. **`origin/feature/b-platform` (`5415245`)**: Included (Task 2). Contains all 24 commits on `origin/feature/b-platform` not in `origin/Hoang` (23 non-merge Dev B + Integrator platform/security/Docker/contract commits plus 1 merge commit `aa9eab9`).
2. **`origin/Nguyen2` (`62c7e5a`)**: Included (Task 3). Because `origin/feature/a-ai-engine` (`cb404fe`) is a strict ancestor of `origin/Nguyen2` (`62c7e5a`), merging `origin/Nguyen2` brings in both `cb404fe` and `TheOrijinnn`'s 3 subsequent commits (`a03536f`, `c5c84cb`, `62c7e5a`). A separate merge of `origin/feature/a-ai-engine` is unnecessary.
3. **`origin/feature/c-frontend-docs` (`74d3319`) AND `origin/TKhanh` (`44a7859`)**: Both included sequentially (Task 4a then Task 4b). Neither is an ancestor of the other: `origin/feature/c-frontend-docs` (`2026-10-23`) contains Dev C's cross-feature tests, visual evidence screenshots, `REPORT.pdf`, and `SLIDES.pdf`/`SLIDES.pptx`, while `origin/TKhanh` (`2026-10-25`) contains `TKhanhJK`'s frontend UX updates for `CR-DEVC-01` and `CR-DEVC-02`.
4. **`origin/Nguyen` (`56c9496`)**: **Excluded.** Single commit from `2026-09-22` (`FIx header UI`) created before the repository was restructured into `frontend/` and `backend/`. It modifies 4 obsolete root-level `UNMAPPED` paths (`package.json`, `package-lock.json`, `run.md`, `src/components/Header.tsx`) that no longer exist in the canonical structure.

---

## 2. Merge Order and Merge Commit Subjects

All merges were executed on `integration/merge-all` using `git merge --no-ff`:

| Order | Source Branch | Source SHA | Merge Commit SHA | Merge Commit Subject |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `origin/feature/b-platform` | `5415245ecf12eabb34620505b5596ec64804c44d` | `306dec92fbc8021bc602edd38431de33229c8973` | `merge: feature/b-platform into integration` |
| **2** | `origin/Nguyen2` | `62c7e5a69bdda626cc57211f8c16b27cc155d45f` | `769f347067b4e82dc910ebe3281297975ff5cf8e` | `merge: origin/Nguyen2 into integration` |
| **3** | `origin/feature/c-frontend-docs` | `74d3319671847f93129f5ef7c85a5ab403319f1d` | `141cb6dca39ed891c13744dadb545634f19447df` | `merge: origin/feature/c-frontend-docs into integration` |
| **4** | `origin/TKhanh` | `44a785937f41f2a73d6028392f8da9c8eb469328` | `ac2fc81288faa8f615d7532aba2aa87946feb18d` | `merge: origin/TKhanh into integration` |

---

## 3. Conflict & Policy Resolution Table

| File | Branches Involved | Policy Rule Applied | What Was Kept | Who Must Confirm |
| :--- | :--- | :--- | :--- | :--- |
| `AI_USAGE.md` | `origin/Hoang` vs `origin/feature/b-platform` | **P8** (`docs/TEAM_ROSTER.md` and `AI_USAGE.md`: take `origin/Hoang`'s version; record other edit as proposal) | Kept `origin/Hoang` (`9fc5443`) version intact; saved `origin/feature/b-platform`'s addition (Case Studies 4 & 5 and Section 4 Benchmark & Evaluation Summary from commit `70f7384`) to `docs/audit/07-alternatives/AI_USAGE-b-platform.patch` | `@BapVitHoang` (Integrator) |
| `docs/requests/devC.md` | `HEAD` (`origin/Hoang`) vs `origin/feature/c-frontend-docs` | **P6** (Per-person logs/requests: keep newest and union any entry from older version) | Kept union containing both `CR-001` (from `origin/feature/c-frontend-docs` & `origin/Hoang`) and `CR-002` (from `origin/Hoang`) | `@TKhanh` (Dev C) & `@BapVitHoang` (Integrator) |
| `docs/notes/C-ai-usage.md` | `HEAD` (`origin/feature/c-frontend-docs`) vs `origin/TKhanh` | **P6** (Same owner has two versions: keep newest and add entry that exists only in older one) | Kept Sessions 1–4, Session 5 (`2026-10-22`, Cross-Feature Offline Tests & Real AI Failure Audit from `feature/c-frontend-docs`), and Session 6 (`2026-10-25`, CR-DEVC-01 & CR-DEVC-02 from `TKhanh`) | `@TKhanh` (Dev C) |

*Note:* After each conflict resolution, `git grep -n "^<<<<<<<\|^>>>>>>>"` confirmed zero conflict markers (**P10**).

---

## 4. Out-of-Lane Edits by Branch

Evaluated against the canonical `OWNERSHIP_MAP` in `scripts/ownership_map.py` (evidence in `docs/audit/07-evidence/task1-inventory.txt`):

| Branch | Mapped Owner(s) | Total Files Changed vs `origin/Hoang` | Out-of-Lane Files | Details |
| :--- | :--- | :---: | :---: | :--- |
| `origin/feature/b-platform` | `devB` + `integrator` | 38 | **0** | 24 `devB` files + 14 `integrator` files (Hoang is both Dev B and Integrator per `docs/TEAM_ROSTER.md`). Note: `AI_USAGE.md` was reverted to `origin/Hoang` per **P8**. |
| `origin/Nguyen2` (includes `origin/feature/a-ai-engine`) | `devA` | 15 | **0** | All 15 modified/added files belong to `devA`. |
| `origin/feature/c-frontend-docs` | `devC` | 23 | **0** | All 23 modified/added files belong to `devC`. |
| `origin/TKhanh` | `devC` | 8 | **0** | All 8 modified files belong to `devC`. |
| `origin/Nguyen` *(Excluded)* | `devA` | 4 | **4 (`UNMAPPED`)** | Pre-restructure commit (`56c9496`, `2026-09-22`) touching root `package.json`, `package-lock.json`, `run.md`, and `src/components/Header.tsx`. Excluded from merge set. |

---

## 5. Files Marked `NEEDS HUMAN DECISION` & Policy P8 Proposals

- **Semantic Conflicts (`NEEDS HUMAN DECISION` per P9):** **0 files.** No semantic conflicts occurred where two branches made incompatible code changes to the same file.
- **Policy P8 Proposal Saved in `docs/audit/07-alternatives/`:**
  - `AI_USAGE.md` -> Patch saved at [`docs/audit/07-alternatives/AI_USAGE-b-platform.patch`](./07-alternatives/AI_USAGE-b-platform.patch). Contains Case Study 4 (Auth Module password/Google ID token signature fix in `eef0af8`), Case Study 5 (Gemini HTTP 400 `GenerateContentConfig` fix in `192fecc` & `afbb08d`), and Section 4 (Benchmark & Evaluation Summary — 24/24 Passed) added in commit `70f7384` on `origin/feature/b-platform`. Kept `origin/Hoang`'s `AI_USAGE.md` per **P8** pending Integrator/human approval in Prompt 5.

---

## 6. Binaries to Regenerate in Prompt 5 (Policy P5)

Per **P5**, all binary files (`png`, `pdf`, `pptx`) from `origin/feature/c-frontend-docs` were taken as-is without merging and are listed below for regeneration/verification in Prompt 5:

| Binary Path | Source Branch | Status / Regeneration Requirement in Prompt 5 |
| :--- | :--- | :--- |
| `docs/REPORT.pdf` | `origin/feature/c-frontend-docs` | **Regenerate in Prompt 5** from updated `docs/REPORT.md` (which includes `origin/TKhanh`'s additions and `origin/Hoang`'s sanitized roster header). |
| `docs/SLIDES.pdf` | `origin/feature/c-frontend-docs` | **Regenerate in Prompt 5** (currently fails `scripts/check_roster.py` with 8 extracted-text violations on Slide 1; tracked in `CR-002`). |
| `docs/SLIDES.pptx` | `origin/feature/c-frontend-docs` | **Regenerate in Prompt 5** (currently fails `scripts/check_roster.py` with 7 extracted-text violations on Slide 1; tracked in `CR-002`). |
| `docs/evidence/agent-dashboard-desktop-1440x900.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5** (regenerate in Prompt 5 if UI screenshots are refreshed). |
| `docs/evidence/agent-dashboard-mobile-375x812.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/agent-ticket-delete-confirm.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/chat-desktop-1440x900.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/chat-mobile-375x812.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/chat-tool-confirmation-card.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/knowledge-manager-desktop.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/knowledge-verification-trace-modal.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/rbac-user-mode-locked.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/telemetry-panel-desktop.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/telemetry-panel-mobile.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/ticket-form-desktop.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |
| `docs/evidence/ticket-form-mobile.png` | `origin/feature/c-frontend-docs` | Taken from Dev C branch per **P5**. |

---

## 7. Pre-Existing Source-Branch & Contract Defects (Not Fixed per Scope Lock)

Per Rule 1 and Tasks 3–5, defects that already existed on a source branch or mismatches between `docs/spec/CONTRACTS.md` and module implementations were **not** fixed during the merge and are cataloged below with their owners:

| ID | Severity | Owner | Evidence (`file:line`) | Suggested Fix |
| :--- | :---: | :---: | :--- | :--- |
| **MRG-DEF-01** | High | `devC` | `docs/SLIDES.pdf` (8 hits) & `docs/SLIDES.pptx` (7 hits) in `docs/audit/07-evidence/task4a-checks.txt` | Regenerate `docs/SLIDES.pptx` and `docs/SLIDES.pdf` in Prompt 5 using neutral GitHub handles from `docs/TEAM_ROSTER.md` per `CR-002`. |
| **MRG-DEF-02** | Medium | `devA` / `integrator` | `docs/notes/A-ai-usage.md:51` & `scripts/check_roster.py:137` in `docs/audit/07-evidence/task3-checks.txt` | Line 51 (`- **AI Tool Used:** Google Antigravity Coding Assistant` followed by role tag) triggers `check_roster.py`'s 4-word name regex. Either remove the trailing role parenthetical in `docs/notes/A-ai-usage.md:51` or exclude `AI Tool Used:` lines in `scripts/check_roster.py`. |
| **MRG-DEF-03** | High | `devC` | `frontend/src/services/api/tickets.ts:337` & `tickets.ts:417` | `updateTicketStatus()` (`PATCH /api/v1/tickets/{id}`) and `regenerateAiDraft()` (`POST /api/v1/agent/tickets/{id}/generate-draft`) omit `getAuthHeaders()`, causing live calls to fail with HTTP 401 against admin-protected endpoints. Attach `getAuthHeaders({ 'Content-Type': 'application/json' })`. |
| **MRG-DEF-04** | High | `devC` | `frontend/src/services/api/documents.ts:159,203,232,288` | `uploadDocument()`, `deleteDocument()`, `verifyDocument()`, and `publishDocument()` omit `getAuthHeaders()`, causing HTTP 401 against `require_role("admin")` in `backend/app/api/v1/endpoints/documents.py`. Attach `getAuthHeaders()` to all 4 requests. |
| **MRG-DEF-05** | High | `devC` | `frontend/src/services/api/workspaces.ts:35,75` | `createWorkspace()` and `updateWorkspace()` omit `getAuthHeaders()`, causing HTTP 401 against `require_role("admin")` in `backend/app/api/v1/endpoints/workspaces.py`. Attach `getAuthHeaders({ 'Content-Type': 'application/json' })`. |
| **MRG-DEF-06** | Medium | `devA` | `backend/app/services/agent_tools.py:234-275,467-471,593-598` | `handle_prepare_ticket_update()` does not store `creator_id`/`creator_email` on the pending action, and `execute_pending_action()` for `update_ticket_priority_or_status` updates ticket priority/status without verifying whether a non-admin `current_user` owns the ticket or has admin role. |
| **MRG-DEF-07** | Low | `devA` / `integrator` | `backend/app/services/rag_service.py:448`, `backend/app/services/ticket_copilot_service.py:186` vs `docs/spec/CONTRACTS.md:55` | `log_ai_call()` is called with `status="config_error"` on `LLMConfigException`, whereas `CONTRACTS.md` §2 specifies `status: Literal["success", "fallback", "refused"]`. Update `CONTRACTS.md` §2 to include `"config_error"` or map to `"fallback"`. |
| **MRG-DEF-08** | Low | `integrator` | `frontend/src/services/api/documents.ts:265`, `backend/app/api/v1/endpoints/documents.py:181` vs `docs/spec/CONTRACTS.md:518` | Both frontend and backend implement `GET /api/v1/documents/{document_id}/verification-report`, whereas `CONTRACTS.md` §8.12 heading states `GET /api/v1/documents/{document_id}/verify`. Update `CONTRACTS.md` §8.12 heading. |
| **MRG-DEF-09** | Low | `devC` | `frontend/src/services/api/tickets.ts:231-258` vs `docs/spec/CONTRACTS.md:437,447` | `getTickets()` defaults `limit` to `50` (instead of `CONTRACTS.md` §8.10 default `20`) and does not read/return the `X-Total-Count` response header for server-driven total page calculation. |

---

## 8. Authorship Table (`origin/Hoang..integration/merge-all`)

Exact output of `git shortlog -sne origin/Hoang..ac2fc81` (across the 4 branch merges prior to audit report commits; no percentages):

```text
    30	Bap <23110020@student.hcmute.edu.vn>
     3	TheOrijinnn <lenguyensonghinh@gmail.com>
     1	TKhanhJK <khanhssaa77@gmail.com>
```

Exact output of `git shortlog -sne origin/Hoang..integration/merge-all` (including the Task 7 audit report commit `ee504da` and the Review Round 1 commit; no percentages):

```text
    32	Bap <23110020@student.hcmute.edu.vn>
     3	TheOrijinnn <lenguyensonghinh@gmail.com>
     1	TKhanhJK <khanhssaa77@gmail.com>
```

---

## 9. Checks and Real Results Summary

All raw command outputs are stored in `docs/audit/07-evidence/`:

| Task / Stage | Check Command | Exit Code | Real Result Summary | Evidence File |
| :--- | :--- | :---: | :--- | :--- |
| **Task 1 (Inventory)** | `task1_inventory.py` | `0` | 6 candidate branches inspected; 0 `.env`, 0 `*.db`, 0 files > 5 MB, 0 real secrets (1 synthetic test key in `test_llm_request_and_circuit_breaker.py:14`). | [`task1-inventory.txt`](./07-evidence/task1-inventory.txt) |
| **Task 2 (After Dev B Merge `306dec9`)** | `python -m pytest backend/tests -q` | `0` | `98 passed, 1 skipped in 12.00s` | [`task2-checks.txt`](./07-evidence/task2-checks.txt) |
| **Task 2 (After Dev B Merge `306dec9`)** | `python scripts/check_roster.py` | `0` | `[PASS] Anti-Fabrication & Roster Gate passed cleanly (0 violations).` | [`task2-checks.txt`](./07-evidence/task2-checks.txt) |
| **Task 2 (After Dev B Merge `306dec9`)** | `python scripts/check_ownership.py --verify-consistency` | `0` | `[PASS] All 209 tracked files are mapped to an owner. Zero overlaps.` | [`task2-checks.txt`](./07-evidence/task2-checks.txt) |
| **Task 3 (After Dev A Merge `769f347`)** | `python -m pytest backend/tests -q` | `0` | `116 passed, 1 skipped in 11.64s` | [`task3-checks.txt`](./07-evidence/task3-checks.txt) |
| **Task 3 (After Dev A Merge `769f347`)** | `python backend/scripts/run_eval.py --mode deterministic` | `0` | `Baseline Pass Rate: 8/24 (33.3%) -> Upgraded Pass Rate: 24/24 (100.0%), Avg Latency: 7.37 ms` | [`task3-checks.txt`](./07-evidence/task3-checks.txt) |
| **Task 3 (After Dev A Merge `769f347`)** | `python scripts/check_roster.py` | `1` | `1 violation` (`docs/notes/A-ai-usage.md:51` pre-existing on `origin/Nguyen2`; logged as `MRG-DEF-02`) | [`task3-checks.txt`](./07-evidence/task3-checks.txt) |
| **Task 3 (After Dev A Merge `769f347`)** | `python scripts/check_ownership.py --verify-consistency` | `0` | `[PASS] All 212 tracked files are mapped to an owner. Zero overlaps.` | [`task3-checks.txt`](./07-evidence/task3-checks.txt) |
| **Task 4a (After `feature/c-frontend-docs` `141cb6d`)** | `npm ci` / `npm run lint` / `npm run build` | `0` | `tsc --noEmit` 0 errors; `vite build` succeeded in `3.30s` (`1699 modules`) | [`task4a-checks.txt`](./07-evidence/task4a-checks.txt) |
| **Task 4a (After `feature/c-frontend-docs` `141cb6d`)** | `python -m pytest backend/tests -q` | `0` | `120 passed, 1 skipped in 9.55s` | [`task4a-checks.txt`](./07-evidence/task4a-checks.txt) |
| **Task 4b (After `origin/TKhanh` `ac2fc81`)** | `npm ci` / `npm run lint` / `npm run build` | `0` | `tsc --noEmit` 0 errors; `vite build` succeeded in `2.63s` (`1699 modules`) | [`task4b-checks.txt`](./07-evidence/task4b-checks.txt) |
| **Task 4b (After `origin/TKhanh` `ac2fc81`)** | `python -m pytest backend/tests -q` | `0` | `120 passed, 1 skipped in 12.04s` | [`task4b-checks.txt`](./07-evidence/task4b-checks.txt) |
| **Task 4b (After `origin/TKhanh` `ac2fc81`)** | `python scripts/check_roster.py` | `1` | `16 violations` (`15` in binary `docs/SLIDES.pdf` & `docs/SLIDES.pptx` [`MRG-DEF-01`] + `1` in `docs/notes/A-ai-usage.md:51` [`MRG-DEF-02`]) | [`task4b-checks.txt`](./07-evidence/task4b-checks.txt) |
| **Task 4b (After `origin/TKhanh` `ac2fc81`)** | `python scripts/check_ownership.py --verify-consistency` | `0` | `[PASS] All 231 tracked files are mapped to an owner. Zero overlaps.` | [`task4b-checks.txt`](./07-evidence/task4b-checks.txt) |
| **Task 6 (Whole-Stack Verification)** | `scripts/verify_setup.ps1` | `1` | `9/10 CHECKS PASSED` (Steps 1–9 PASS including `120 passed, 1 skipped` pytest, `tsc --noEmit`, `vite build`, `docker-compose.yml`, and ownership; Step 10 reports the 16 pre-existing `check_roster.py` hits) | [`task6-verify-setup.txt`](./07-evidence/task6-verify-setup.txt) |
| **Task 6 (Docker Build & Smoke Test)** | `docker compose build` + `scripts/smoke_docker.ps1` + `docker compose down` | `0` | `ALL DOCKER & POSTGRESQL SMOKE CHECKS PASSED!` (8/8 checks: Postgres 16 + `pgvector 0.8.6`, `/api/v1/health` connected, Nginx HTTP 200 & `/api/v1/` proxy, Demo admin login, wrong password 401, unauthenticated `/tickets` 401, authenticated `/tickets` HTTP 200 with `X-Total-Count=43` and `page=2` returning 10 tickets, SSE `proxy_buffering off`) | [`task6-docker-smoke.txt`](./07-evidence/task6-docker-smoke.txt) |

---

## 10. How to Undo (Safety Net & Rollback Instructions)

1. **Local Backup Branches (Created in Task 0 before any merge):**
   - `backup/merge-Hoang` -> `9fc5443bf0d153b4ecbe4be8bfe48d5856fd1b26`
   - `backup/merge-feature/b-platform` -> `5415245ecf12eabb34620505b5596ec64804c44d`
   - `backup/merge-feature/a-ai-engine` -> `cb404fecb89874bcc74be0954ebea933f671215b`
   - `backup/merge-feature/c-frontend-docs` -> `74d3319671847f93129f5ef7c85a5ab403319f1d`
   - `backup/merge-Nguyen2` -> `62c7e5a69bdda626cc57211f8c16b27cc155d45f`
   - `backup/merge-TKhanh` -> `44a785937f41f2a73d6028392f8da9c8eb469328`
   - `backup/merge-Nguyen` -> `56c9496b0760f8f2f58a9e58b29d5ce7aac209a8`
2. **Untouched Branches & Worktrees:**
   - `Hoang`, `master`, and all teammate remote branches (`origin/feature/*`, `origin/Nguyen2`, `origin/TKhanh`, `origin/Nguyen`) were **not** modified or pushed to.
   - Worktrees `smartdesk-ai`, `smartdesk-A`, `smartdesk-B`, and `smartdesk-C` were untouched.
3. **To Remove the Merge Worktree (While Keeping `integration/merge-all` for Inspection):**
   ```powershell
   Set-Location "D:\SPKT_2023\year_4\newtech\smartdesk-ai"
   git worktree remove ..\smartdesk-merge
   ```
   *(Note: Do NOT run `git worktree remove` until human inspection and fast-forward into `Hoang` are complete.)*

---

## Review round 1

- **Skeptical Verifier (`8ff53ad6-4f20-4d05-ba32-69c8b449be6e`):** `VERDICT: FAIL`
  - *Finding 1:* Section 1.3 stated `origin/feature/b-platform` had `22` commits on top of `origin/Hoang`, whereas `task1-inventory.txt:17` and `git rev-list --count origin/Hoang..origin/feature/b-platform` show `24` commits (23 non-merge commits + 1 merge commit `aa9eab9`).
  - *Finding 2:* Sections 3 and 5 described `docs/audit/07-alternatives/AI_USAGE-b-platform.patch` as containing "Section 3.7 log entry", whereas `AI_USAGE-b-platform.patch` actually contains Case Study 4 (`eef0af8`), Case Study 5 (`192fecc` & `afbb08d`), and Section 4 (Benchmark & Evaluation Summary — 24/24 Passed) from commit `70f7384`.
  - *Finding 3:* Section 8 showed `30 Bap` (before report commit) without also showing the updated count on `HEAD` including the report/review commits.
- **Requirements and Honesty Auditor (`22823912-b17c-49c3-9122-606567724590`):** `VERDICT: FAIL`
  - Confirmed Tasks 0–7 and test integrity are satisfied, and reported the same 3 documentation accuracy findings in `docs/audit/07-merge-report.md` (lines 71, 95, 121, 173).
- **Security and Robustness Reviewer (`6dccd193-8f5b-4d0e-92d5-0985ac503c00`):** `VERDICT: PASS`
  - Confirmed zero leaked secrets, intact auth/RBAC/proxy hardening, non-blocking async concurrency, and accurate cataloging of all pre-existing source-branch security/auth/contract defects (`MRG-DEF-01`..`MRG-DEF-09`).
- **Ownership and Conflict Hunter (`993a5187-140e-4b46-8b23-7071a4b078dd`):** `VERDICT: PASS`
  - Confirmed all modified files conform to `ALLOWED PATHS`, Policy P8 is preserved (`docs/TEAM_ROSTER.md` and `AI_USAGE.md` identical to `origin/Hoang`), zero conflict markers remain, and all 241 tracked files map cleanly in `scripts/ownership_map.py`.
- **Fixes Applied After Round 1:**
  - Updated Section 1.3 commit count to `24` (23 non-merge + 1 merge commit `aa9eab9`).
  - Updated Sections 3 and 5 to accurately describe `docs/audit/07-alternatives/AI_USAGE-b-platform.patch` (Case Studies 4 & 5 and Section 4 Benchmark & Evaluation Summary from commit `70f7384`).
  - Updated Section 8 to show both `git shortlog -sne origin/Hoang..ac2fc81` (`30 Bap`) and `git shortlog -sne origin/Hoang..integration/merge-all` (`32 Bap`).


