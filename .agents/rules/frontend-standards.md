# Frontend Development Rules & Standards

## 1. Stack & Directory Organization
- Framework: **React 19 + Vite 6 + Tailwind CSS v4 + TypeScript** (SPA, NOT Next.js).
- Directory layout:
  - `frontend/src/components/`: Core screen views as thin coordinators (`Header.tsx`, `ChatView.tsx`, `TicketFormView.tsx`, `AgentDashboardView.tsx`, `KnowledgeManagerView.tsx`, `Footer.tsx`).
  - `frontend/src/features/`: Modular feature components for parallel team development (`agent/`, `auth/`, `chat/`, `knowledge/`, `telemetry/`).
  - `frontend/src/services/api/`: Modular API client services (`client.ts`, `chat.ts`, `tickets.ts`, `workspaces.ts`, `documents.ts`, `auth.ts`, `telemetry.ts`).
  - `frontend/src/services/api.ts`: Centralized re-export facade preserving 100% backward compatibility.
  - `frontend/src/services/mocks/`: Mock fixtures for offline and deterministic development.
  - `frontend/src/types/`: Modular TypeScript definitions (`common.ts`, `chat.ts`, `ticket.ts`, `workspace.ts`, `document.ts`, `auth.ts`, `telemetry.ts`).
  - `frontend/src/types.ts`: Centralized types re-export facade (FROZEN CONTRACT).
  - `frontend/src/data.ts`: Mock and offline fallback data.
  - `frontend/src/App.tsx`: Root coordinator managing active tabs, demo states, and global notifications.

## 2. API & Network Calling Convention
- **DO NOT** use `fetch()` or `axios` directly in React components.
- **DO** call functions from `frontend/src/services/api/` or the facade `frontend/src/services/api.ts` (e.g. `createTicket()`, `getTickets()`, `sendChatMessage()`, `updateTicketStatus()`, `regenerateAiDraft()`, `checkBackendHealth()`).
- **Offline Resilience:** If the backend cannot be reached, the API client automatically returns fallback data and notifies the UI via `notifyFallback()`. The UI must never crash on network failure.

## 3. Ticket Status & Category Mapping
Always use the canonical conversion functions when dealing with ticket statuses:
- Backend format: `"open"`, `"in_progress"`, `"resolved"`
- Frontend format: `"Open"`, `"Pending"`, `"Resolved"`
- Helpers: `mapBackendStatusToFrontend()`, `mapFrontendStatusToBackend()` in `frontend/src/services/api.ts`.
- Canonical Categories: `'Authentication' | 'Billing' | 'Bug Report' | 'Feature Request' | 'General'`.

## 4. Design Tokens & Visual Hierarchy
Refer to `docs/DESIGN.md` for exact styles:
- Primary Brand: `bg-indigo-600 hover:bg-indigo-700 text-white`
- AI Badge / Citation: `bg-violet-50 text-violet-700 border-violet-200`
- Urgent Priority: `bg-rose-50 text-rose-700 border-rose-200`
- Caution / Fallback: `bg-amber-50 text-amber-700 border-amber-200`
- Resolved / Success: `bg-emerald-50 text-emerald-700 border-emerald-200`

## 5. Language, Ownership & Pre-Commit Check
- All customer and agent visible UI copy must be in **Vietnamese**.
- Technical names, identifiers, code, and types must remain in **English**.
- Shared files (`types.ts`, `api.ts`, `App.tsx`) may only be edited via the Integration Owner.
- Ownership: Run `python scripts/check_ownership.py --staged` to ensure no cross-owner boundary violations.
- Run `npm run lint --prefix frontend; npm run build --prefix frontend` before every commit.
