# Developer B — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.

---

## Session 1: User Model & Role-Based Access Control
- **Date:** 2026-10-20
- **AI Tool Used:** Gemini 3.5 Flash / Claude 3.5 Sonnet
- **Key Prompt:** "Implement User ORM model with role enum ('admin', 'user') and OAuth2 JWT dependency get_current_user in FastAPI."
- **Manual Verification & Changes:** Verified that `get_current_user` extracts Bearer token, decodes JWT, and queries DB. Added `conftest.py` default admin token so unauthenticated tests don't break.
- **Bug / Failure Case Study (Mandatory):**
  - *Observed Issue:* AI helper initially used synchronous `db.query(User)` inside the async FastAPI dependency, blocking the ASGI event loop.
  - *Fix:* Replaced with `await db.execute(select(User).filter_by(id=user_id))` using SQLAlchemy 2.0 async syntax.
