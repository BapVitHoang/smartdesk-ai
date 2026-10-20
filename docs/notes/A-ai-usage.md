# Developer A — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.

---

## Session 1: Single-Call Ticket Copilot Structured Output
- **Date:** 2026-10-20
- **AI Tool Used:** Gemini 3.5 Flash / Claude 3.5 Sonnet
- **Key Prompt:** "Implement Pydantic v2 model TicketCopilotStructuredOutput and combine triage + draft reply into one single LLM call."
- **Manual Verification & Changes:** Checked that sentiment is constrained to `positive | neutral | negative` and priority maps to canonical SLA hours. Verified against `CONTRACTS.md`.
- **Bug / Failure Case Study (Mandatory):**
  - *Observed Issue:* Initial AI generation omitted the `ai_draft_reply` field when confidence was below 0.7, causing Pydantic validation error.
  - *Fix:* Added default fallback draft string generation in Python to ensure valid schema compliance even on low-confidence inputs.
