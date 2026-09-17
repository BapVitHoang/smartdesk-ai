# Security, Fallback & RAG Guardrails

## 1. Google Gemini Latency & Circuit Breaker
- Maximum timeout for LLM calls: **4.0 seconds** (enforced via `asyncio.wait_for(..., timeout=4.0)`).
- If timeout, rate limit (HTTP 429), or API error occurs:
  1. Log warning.
  2. Call `FallbackService.match_faq()` using BM25 against `backend/data/seed_faq.json`.
  3. Return HTTP 200 with `"is_fallback": true`, citation list, and ticket escalation recommendation.

## 2. Prompt Injection & Input Sanitization
- File: `backend/app/core/security.py`
- All incoming chat messages and ticket descriptions must pass through:
  - `sanitize_input(text)`: Truncate max characters and strip non-printable characters.
  - `check_prompt_injection(text)`: Reject jailbreak phrases (e.g., `ignore previous instructions`, `system prompt reveal`, `developer mode`).
- On detection, immediately raise `InvalidPromptException` returning HTTP 400 (`PROMPT_SECURITY_VIOLATION`).

## 3. Grounding & Anti-Hallucination
- LLM system prompt temperature must be set to `0.2` for customer support RAG.
- Model must be strictly instructed: *"If the provided context does not contain enough information to answer truthfully, explicitly say you do not know and recommend escalating to a human support agent."*
- Every answer must include structured citations matching knowledge IDs (`doc-01`, etc.).

## 4. Secret Management
- NEVER write real API keys in source code, default config files, or frontend environment files.
- Real API keys belong ONLY in `backend/.env` (gitignored).
