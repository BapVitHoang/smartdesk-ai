# Frontend Feature Modules (`frontend/src/features/`)

This directory provides isolated extension points for parallel frontend development so multiple developers/agents can build new UI features without causing merge conflicts in `frontend/src/components/`.

## Module Ownership
- `features/auth/` — **Owner 2**: Login modal, Google OAuth2 callback button, and role badge UI.
- `features/telemetry/` — **Owner 1**: AI Usage, Latency, and Evaluation metrics panel.
- `features/chat/` — **Owner 1 / Owner 3**: SSE streaming indicator and Agent Tool confirmation cards.

## Rules
1. Never call `fetch()` directly; always use `frontend/src/services/api.ts`.
2. All user-facing text must be in **Vietnamese**; all identifiers and types in **English**.
3. Follow the Tailwind CSS v4 design tokens defined in `docs/DESIGN.md`.
