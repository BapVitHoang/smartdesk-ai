# Security, Fallback & RAG Guardrails

## 1. Google Gemini / Ollama Latency & Cost-Guard Circuit Breaker
- Maximum timeout for Cloud LLM calls: **4.0 seconds** (enforced via `asyncio.wait_for(..., timeout=4.0)`).
- Primary Cloud model: `gemini-3.5-flash-lite` (with automatic fallback to `gemini-2.5-flash-lite`); Embeddings: `gemini-embedding-001`.
- Local Ollama provider (`AI_PROVIDER=ollama`): `qwen2.5:3b` and `nomic-embed-text`.
- If timeout, rate limit (HTTP 429 `ResourceExhausted`), or API error occurs:
  1. Log warning and set 60-second Cost-Guard cooldown (`cooldown_until = time.time() + 60.0`) on HTTP 429.
  2. Call `FallbackService.match_faq()` using BM25 against `backend/data/seed_faq.json`.
  3. Return HTTP 200 with `"is_fallback": true`, citation list, and ticket escalation recommendation.

## 2. Prompt Injection & Input Sanitization
- File: `backend/app/core/security.py`
- All incoming chat messages and ticket descriptions must pass through:
  - `sanitize_input(text)`: Truncate max characters and strip non-printable control characters.
  - `check_prompt_injection(text)`: Reject jailbreak phrases in English and Vietnamese (e.g., `ignore previous instructions`, `system prompt reveal`, `developer mode`, `bỏ qua hướng dẫn trước`).
- On detection, immediately raise `InvalidPromptException` returning HTTP 400 (`PROMPT_SECURITY_VIOLATION`).

## 3. Grounding & Anti-Hallucination
- LLM system prompt temperature must be set to `0.2` for customer support RAG.
- Prompts are managed centrally via `backend/data/prompts.json` and `backend/app/core/prompts.py`.
- Model must be strictly instructed: *"If the provided context does not contain enough information to answer truthfully, explicitly say you do not know and recommend escalating to a human support agent."*
- Every answer must include structured citations matching knowledge IDs (`doc-01`, etc.).

## 4. Secret Management
- NEVER write real API keys in source code, default config files, or frontend environment files.
- Real API keys belong ONLY in `backend/.env` (gitignored). Never commit `.env` or `*.db` files.
