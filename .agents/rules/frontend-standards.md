# Frontend Development Rules & Standards

## 1. Stack & Directory Organization
- Framework: **React 19 + Vite 6 + Tailwind CSS v4 + TypeScript**.
- Directory layout:
  - `src/components/`: Presentational and modular screen views (`Header.tsx`, `ChatView.tsx`, `TicketFormView.tsx`, `AgentDashboardView.tsx`, `Footer.tsx`).
  - `src/services/api.ts`: Centralized API communication layer with automatic offline fallback.
  - `src/types.ts`: Shared TypeScript types and interfaces.
  - `src/data.ts`: Mock and offline fallback data.
  - `src/App.tsx`: Root coordinator managing active tabs, demo states, and global notifications.

## 2. API & Network Calling Convention
- **DO NOT** use `fetch()` or `axios` directly in React components.
- **DO** call functions from `src/services/api.ts` (e.g. `createTicket()`, `getTickets()`, `sendChatMessage()`, `updateTicketStatus()`, `regenerateAiDraft()`, `checkBackendHealth()`).
- **Offline Resilience:** If the backend cannot be reached, the API client automatically returns fallback data and notifies the UI via `notifyFallback()`. The UI must never crash on network failure.

## 3. Ticket Status Mapping
Always use the canonical conversion functions when dealing with ticket statuses:
- Backend format: `"open"`, `"in_progress"`, `"resolved"`
- Frontend format: `"Open"`, `"Pending"`, `"Resolved"`
- Helpers: `mapBackendStatusToFrontend()`, `mapFrontendStatusToBackend()` in `src/services/api.ts`.

## 4. Design Tokens & Visual Hierarchy
Refer to `DESIGN.md` for exact styles:
- Primary Brand: `bg-indigo-600 hover:bg-indigo-700 text-white`
- AI Badge / Citation: `bg-violet-50 text-violet-700 border-violet-200`
- Urgent Priority: `bg-rose-50 text-rose-700 border-rose-200`
- Caution / Fallback: `bg-amber-50 text-amber-700 border-amber-200`
- Resolved / Success: `bg-emerald-50 text-emerald-700 border-emerald-200`

## 5. Language & Localization
- All customer and agent visible UI copy must be in **Vietnamese**.
- Technical names, identifiers, code, and types must remain in **English**.
