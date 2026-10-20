# Developer C — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.

---

## Session 1: SSE Token Streaming in React ChatView
- **Date:** 2026-10-20
- **AI Tool Used:** Gemini 3.5 Flash / Claude 3.5 Sonnet
- **Key Prompt:** "Implement SSE token consumption with fetch and ReadableStream in chat.ts, updating React state token by token with cursor."
- **Manual Verification & Changes:** Verified that `ReadableStream` reader decodes chunks as UTF-8, strips SSE event prefixes (`data:`), and handles stream termination cleanly.
- **Bug / Failure Case Study (Mandatory):**
  - *Observed Issue:* AI helper created an infinite loop by re-triggering `useEffect` on every token chunk append.
  - *Fix:* Replaced `useEffect` dependency with an imperative async function triggered directly on user submit event.
