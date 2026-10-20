# Developer Onboarding Guide — Start Here

> **Welcome to the SmartDesk AI Engineering Team!**  
> This document is your primary onboarding manual. Read this document completely **before** opening your editor or writing any code. Following these instructions guarantees you will build high-quality features, avoid merge conflicts, and protect your individual grade.

---

## 1. Mandatory Reading Order

Spend 60 minutes reading these 5 documents before starting your implementation. Do not skip any of them.

| # | Document | Time | Why You Must Read It Now |
| :-: | :--- | :-: | :--- |
| **1** | [**`docs/DEV_START_HERE.md`**](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/docs/DEV_START_HERE.md) *(this file)* | 10m | Understand project rules, safety gates, and how your grade is evaluated. |
| **2** | [**`docs/plan/WORKSTREAMS.md`**](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/docs/plan/WORKSTREAMS.md) | 15m | Identify your assigned workstream (Dev A, B, or C), owned files, and Demo Script. |
| **3** | [**`docs/spec/CONTRACTS.md`**](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/docs/spec/CONTRACTS.md) | 15m | Learn the exact function signatures and schemas used to communicate across modules. |
| **4** | [**`docs/plan/GIT_WORKFLOW.md`**](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/docs/plan/GIT_WORKFLOW.md) | 10m | Learn branch naming, daily rebase habits, and the pre-commit verification gate. |
| **5** | [**`docs/ARCHITECTURE.md`**](file:///d:/SPKT_2023/year_4/newtech/smartdesk-ai/docs/ARCHITECTURE.md) | 10m | Understand the system architecture, dual-mode LLM fallback, and dual-database design. |

---

## 2. Environment Setup & Verification (PowerShell)

SmartDesk AI uses Python 3.11+ asynchronous FastAPI and Node.js 20+ React 19. Complete setup takes approximately 5 minutes.

### Step-by-Step Setup
```powershell
# 1. Clone the repository (if not already in workspace)
git clone https://github.com/hoangduong140604/smartdesk-ai.git
cd smartdesk-ai

# 2. Check out your designated feature branch
# (Choose: feature/a-ai-engine, feature/b-platform, or feature/c-frontend-docs)
git checkout -b feature/<your-branch> origin/Hoang

# 3. Create backend virtual environment and install dependencies
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
cd ..

# 4. Install frontend npm dependencies
cd frontend
npm install
cd ..

# 5. Run the universal automated verification script
powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1
```

> [!IMPORTANT]
> `scripts/verify_setup.ps1` runs 8 automated checks (Git branch, backend `.env`, Python version, node_modules, pytest zero-key suite, npm lint, npm build, and Docker config). **You must see `ALL 8/8 CHECKS PASSED` before proceeding.**

---

## 3. The 11 Golden Rules of SmartDesk AI

1. **Stay in Your Assigned Lane:** Never edit a file owned by another developer or a frozen contract file. (Violations trigger build failure in `check_ownership.py`).
2. **Never Commit Secrets:** API keys, passwords, and `.env` files must NEVER be staged or committed. (A single secret in Git deducts 5% from the entire team under CRIT-10).
3. **Never Discard Code Destructively:** `git reset --hard`, `git push --force`, and `git clean -fd` are strictly forbidden. Always create a backup branch before any refactor.
4. **All LLM Calls Must Go Through Backend:** Frontend code must never import `@google/genai` or store Google API keys. (Violations deduct 5% under REQ-08).
5. **No Synchronous Blocking I/O:** Every database query, network call, and LLM invocation must use `async` / `await`. Never use `requests.get()` or `time.sleep()`.
6. **Graceful Fallback Mode:** The app must function reliably when Gemini API is rate-limited or offline. Never crash on external HTTP 429 or network errors.
7. **Strict Pydantic Validation:** Every API request and response must be typed with Pydantic v2 models. Raw dicts in route handlers are forbidden.
8. **Vietnamese Language for UI:** All customer-facing messages, buttons, and placeholders must be in natural Vietnamese. (Code and comments remain in English).
9. **No Silent Error Fabrication:** When an API fails, display a clear Vietnamese error toast. Never fabricate fake entities in localStorage.
10. **Conventional Commit Messages:** Every commit must follow `feat:`, `fix:`, `test:`, `docs:`, or `refactor:`.
11. **Log Every AI Prompt in Your AI Log:** Maintain `docs/notes/<dev>-ai-usage.md` with your prompts and verification checks. (Missing logs deduct 10% under CRIT-09).

---

## 4. How to Use AI Coding Agents Safely

Using AI assistants (Claude, Cursor, Copilot, ChatGPT) is encouraged, but **you are personally responsible for every line of code committed.**

### 4.1 Prompting Tips & Context Management
- **Provide Explicit Boundaries:** Always paste your assigned file list and tell the AI: *"Only modify files in my workstream. Do not touch config.py, CONTRACTS.md, or any file outside my list."*
- **Keep Prompts Focused:** Work task by task. Do not ask the AI to implement multiple PLAN.md tasks in a single prompt.
- **Always Test Before Committing:** Run `pytest` and `npm run lint` immediately after applying AI code.

### 4.2 Logging AI Usage (`docs/notes/<dev>-ai-usage.md`)
Whenever you use an AI tool to generate code:
1. Record the tool name (e.g., Cursor, Claude 3.5 Sonnet).
2. Record the key prompt used.
3. Record what you manually checked, changed, or tested.
4. **Mandatory Case Studies:** You must document at least **one instance** where the AI produced incorrect, buggy, or hallucinated code and explain how you fixed it. (Required to satisfy **REQ-28** and avoid the -10% group penalty under **CRIT-09**).

### 4.3 The CRIT-08 "Understanding Gate" (50% Score Cap Warning!)
> [!CAUTION]
> **Read this carefully:** In the final oral defense, each student is interviewed individually.
> If you cannot explain your module's architecture or cannot trace one of your user stories to its exact source code line and test, **your individual grade will be capped at 50% of the team grade**, even if the product works perfectly!
> **Rule:** Never commit code you do not fully understand.

---

## 5. Known Pitfalls Specific to Your Workstream

Review the pitfalls discovered during our project audit before writing code:

### Dev A (AI Engine & Evaluation)
- **Gemini Free Tier 15 RPM Rate Limit:** The Gemini API has a strict 15 requests/minute quota. Always use single-pass structured output (combine triage + drafting into 1 LLM call) and implement `asyncio.sleep(4.5)` throttling in `run_eval.py --mode live`.
- **Circuit Breaker False Triggers:** If an external LLM call returns 429, the system enters a 60-second cooldown. Always provide a 1-click cooldown reset in `endpoints/ai_usage.py`.
- **Hallucinated Refusal Answers:** System prompt must strictly command the model to answer only from provided context, or explicitly say it cannot find the answer and recommend human escalation.

### Dev B (Platform, Data & Security)
- **SQLite vs PostgreSQL `pgvector` Types:** Local development uses SQLite while Docker/production uses PostgreSQL with `pgvector`. Always use `Vector(768).with_variant(JSON(), "sqlite")` in `models/knowledge.py`.
- **Raw `str(e)` Leaks:** Never return `detail=str(e)` in HTTP 500 responses; this leaks internal stack traces and database paths to clients. Log the exception internally and return a generic error message.
- **Auth Token Breakage in Existing Tests:** When securing endpoints with `Depends(get_current_user)`, ensure `backend/tests/conftest.py` attaches a valid demo admin JWT so existing unit tests do not break.

### Dev C (Frontend UX, QA & Docs)
- **`ApiError` Swallowing:** Never swallow HTTP 400 validation errors or 401/403 authorization failures with silent fallbacks. Surface errors clearly to the user.
- **Mobile Responsive Split-Pane:** On mobile viewports ($375\times812$), avoid hardcoding `h-full` on flexbox columns; use `h-1/2 md:h-full` to keep both list and detail views scrollable.
- **SSE Stream Re-Renders:** When streaming tokens in React, append chunks efficiently using state updater functions (`prev => prev + chunk`) rather than re-creating arrays.

---

## 6. Daily Communication & Sync Protocol

- **Daily Standup Check-in (Async / Chat):** Post a 3-bullet update each morning:
  1. What I completed yesterday.
  2. What I am working on today.
  3. Any blockers or change requests needed from other modules.
- **Need a Change in Shared Files?** Create an entry in `docs/requests/<your-dev-id>.md`.
- **Pre-PR Verification:** Run `powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1` before submitting any PR.
