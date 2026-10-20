# ADR-004: React 19 + Vite 6 Single Page Application (SPA) with Dual-Mode Offline Client

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** SmartDesk AI Architecture Team (`Owner 3: Frontend UX & QA`)

## 1. Context
Early project proposal drafts considered Next.js 14 (SSR). However, SmartDesk AI's primary UX consists of highly interactive, stateful client views (real-time RAG chat with workspace switching, live-validated ticket creation, split-pane agent triage dashboard, and interactive verification modals) communicating with an independent Python FastAPI backend.

## 2. Decision
We standardized the frontend on **React 19 + Vite 6 + Tailwind CSS v4 + TypeScript** (`frontend/src/`) as a clean Single Page Application (SPA) with a centralized API service layer (`frontend/src/services/api.ts`):
1. **Strict Separation of Concerns:** All backend logic, database access, and LLM keys reside strictly in the FastAPI backend (`:8000`); the frontend (`:3000`) is a pure TypeScript SPA with zero server-side secrets.
2. **Centralized Dual-Mode API Client (`frontend/src/services/api.ts`):** UI components never call `fetch()` directly. Every API helper (`sendChatMessage`, `getTickets`, `createTicket`, `verifyDocument`, etc.) wraps `fetchWithTimeout` and automatically falls back to deterministic local mock data (`frontend/src/data.ts`) with a Vietnamese warning toast (`notifyFallback`) if the backend is offline.
3. **Explicit 4-State UI Controller:** Every view supports `Loading`, `Empty`, `Success`, and `Error / Fallback` states toggleable from `Header.tsx` for deterministic grading and live demos.

## 3. Alternatives Considered
- **Next.js 14 App Router (SSR):** Rejected because splitting backend logic between Next.js API routes and FastAPI creates duplicated validation contracts and complicates offline fallback handling.

## 4. Consequences
- **Positive:** Sub-10s production builds (`vite build`), zero SSR hydration bugs, and 100% crash-free UI behavior even if the backend container is stopped mid-demo.
- **Negative / Trade-off:** Requires CORS configuration (`CORS_ORIGINS`) between `:3000` (or `:5173`) and `:8000` during local development.
