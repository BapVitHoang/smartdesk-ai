---
name: react-frontend-builder
description: >-
  Develop, maintain, and test the React 19 + Vite 6 + Tailwind CSS v4 frontend for SmartDesk AI.
  Use when building or modifying UI components (Header, ChatView, TicketFormView, AgentDashboardView),
  integrating API client methods in src/services/api.ts, handling offline fallback states,
  or styling views using Tailwind CSS tokens from DESIGN.md.
---

# React Frontend Builder Skill for SmartDesk AI

This skill guides the AI assistant through developing, maintaining, and styling the single-page application (SPA) frontend for **SmartDesk AI**.

---

## 1. Stack & Architecture Overview

- **Core Framework:** React 19, TypeScript (~5.8), Vite 6.
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`), Lucide Icons (`lucide-react`), Framer Motion (`motion`).
- **Application Type:** Client-side SPA (Single Page Application). **NOT** Next.js.
- **Root Layout:**
  - `src/App.tsx`: Controls active tab (`'chat' | 'ticket' | 'agent'`), demo state (`'success' | 'loading' | 'empty' | 'error'`), and global toast notifications.
  - `src/components/Header.tsx`: Navigation tabs, health status badge, demo state switcher.
  - `src/components/ChatView.tsx`: Customer AI chat interface with citation pills and fallback alerts.
  - `src/components/TicketFormView.tsx`: Ticket submission form with live validation and SLA calculator.
  - `src/components/AgentDashboardView.tsx`: Support agent triage table, live search/filtering, and AI Copilot draft review panel.
  - `src/components/Footer.tsx`: Latency metrics and system version badge.

---

## 2. API Integration & Offline Fallback Rules

### Centralized Service Layer
All network communications must pass through [`src/services/api.ts`](../../../src/services/api.ts). NEVER use raw `fetch()` or `axios` inside UI components.

Available service functions:
```typescript
import {
  sendChatMessage,       // (message, sessionId?, onToast?) => Promise<{ response, citations, ... }>
  getTickets,            // (filters?, onToast?) => Promise<Ticket[]>
  createTicket,          // (formData, onToast?) => Promise<Ticket>
  updateTicketStatus,    // (ticketId, status, aiDraftReply?, onToast?) => Promise<Ticket>
  regenerateAiDraft,     // (ticketId, onToast?) => Promise<Ticket>
  checkBackendHealth,    // () => Promise<{ status, database?, version? }>
} from '../services/api';
```

### Dual-Mode Graceful Fallback
If the backend is offline, unresponsive, or returns network errors:
1. `src/services/api.ts` catches the error.
2. It calls `notifyFallback(message, 'warning')` to render a non-intrusive toast.
3. It returns localized fallback data from `src/data.ts` (`INITIAL_TICKETS`, `getRagResponse`).
4. **The UI must NEVER throw an unhandled exception or render a blank screen.**

---

## 3. UI/UX Tokens & Tailwind CSS v4 Guidelines

Always use the design system defined in [`DESIGN.md`](../../../DESIGN.md):
- **Brand Primary:** `bg-indigo-600 hover:bg-indigo-700 text-white`
- **AI Accent / Citations:** `bg-violet-50 text-violet-700 border-violet-200`
- **Urgent Priority:** `bg-rose-50 text-rose-700 border-rose-200`
- **Caution / Warning / Fallback:** `bg-amber-50 text-amber-700 border-amber-200`
- **Resolved / Success:** `bg-emerald-50 text-emerald-700 border-emerald-200`
- **Neutral Card Surface:** `bg-white border border-slate-200 shadow-sm rounded-xl`

### 4 Interaction States
Every view must gracefully handle all four operational states:
1. **Loading:** Display subtle skeleton pulse (`animate-pulse`) or spinning Lucide icon (`Loader2`).
2. **Empty:** Friendly Vietnamese empty state message with an actionable button.
3. **Success:** Clear visual confirmation (e.g., ticket created modal, badge update).
4. **Error / Fallback:** Amber banner explaining fallback mode with an escalation button.

---

## 4. Status Mapping Reference

When updating ticket statuses in UI components, always use the conversion helpers:
- Backend: `"open"`, `"in_progress"`, `"resolved"`
- Frontend: `"Open"`, `"Pending"`, `"Resolved"`

```typescript
import { mapBackendStatusToFrontend, mapFrontendStatusToBackend } from '../services/api';
```

---

## 5. Development & Verification Commands

```bash
# Start Vite dev server on port 3000
npm run dev

# TypeScript typecheck without emitting
npm run lint

# Production build check
npm run build
```
