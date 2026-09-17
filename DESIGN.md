# SmartDesk AI – UI/UX & System Design Document
> **Project:** SmartDesk AI – Intelligent Customer Support & Knowledge Synthesizer  
> **Document:** Enterprise UI/UX & Interaction Design Specifications  
> **Target Platform:** Responsive Web (Next.js 14 / React + Tailwind CSS)

---

## 1. Design Overview & Objectives

### 1.1 Core Objectives
- **Simplicity & Efficiency:** Keep interfaces minimal, clear, and high-contrast, avoiding unnecessary cognitive overhead for both customers and support agents.
- **Immediate Value Demonstration:** Prove the vertical slice experience within seconds—from customer query and citation, to fallback escalation, to agent resolution.
- **Transparent State Handling:** Explicitly represent all operational states (`Loading`, `Empty`, `Success`, `Error / Fallback`) with clear visual cues.
- **Mobile-First Responsiveness:** Seamless transition between desktop widescreen dashboards and mobile-friendly conversational interfaces.

---

## 2. Design System & Visual Foundations

### 2.1 Color Palette
Designed around a clean, enterprise-grade SaaS aesthetic utilizing Tailwind CSS color variables:

| Category | Tailwind Class | Hex Code | Semantic Role |
| :--- | :--- | :--- | :--- |
| **Primary (Brand)** | `indigo-600` | `#4F46E5` | Primary buttons, active tabs, AI assistant badges |
| **Primary Hover** | `indigo-700` | `#4338CA` | Button hover & active states |
| **Neutral Dark** | `slate-900` | `#0F172A` | Primary text headings, dark navbar elements |
| **Neutral Body** | `slate-600` | `#475569` | Secondary text, descriptions, timestamps |
| **Neutral Border** | `slate-200` | `#E2E8F0` | Card borders, dividers, form field borders |
| **Neutral Surface**| `slate-50` / `white` | `#F8FAFC` / `#FFF` | App background and card surfaces |
| **Success** | `emerald-600` | `#059669` | Ticket resolved, submission success, positive feedback |
| **Warning / Caution**| `amber-500` | `#F59E0B` | Medium priority, fallback notices, pending queue |
| **Danger / Error** | `rose-600` | `#E11D48` | Form validation errors, AI outage alerts, urgent priority |
| **AI Accent** | `violet-500` | `#8B5CF6` | AI citation tags, RAG thinking indicators, draft pill |

### 2.2 Typography Hierarchy
- **Font Family:** Inter / System UI (`font-sans`), clean sans-serif optimized for legibility.
- **Scale:**
  - `text-2xl` (24px, SemiBold): Screen headers and page titles.
  - `text-lg` (18px, Medium): Section headers, modal titles.
  - `text-sm` (14px, Regular/Medium): Body text, form inputs, table data, chat messages.
  - `text-xs` (12px, Regular/SemiBold): Badges, timestamps, citations, error captions.

### 2.3 Iconography & Component Tokens
- **Icon Set:** `lucide-react` (e.g., `MessageSquare`, `LifeBuoy`, `Inbox`, `AlertCircle`, `CheckCircle2`, `RefreshCw`, `Send`, `FileText`).
- **Corner Radii:** Cards and panels (`rounded-xl`), buttons and inputs (`rounded-lg`), badges and pills (`rounded-full`).
- **Elevation:** Subtle shadows (`shadow-sm`, `shadow-md`) to separate overlay states without visual clutter.

---

## 3. Information Architecture & Navigation

```
+-----------------------------------------------------------------------------------+
|  [Logo] SmartDesk AI                 (Demo State: [Loading] [Empty] [Success] [Error]) |
|  Navigation Tabs: [ 💬 AI Chat Assistant ]  [ 📝 Submit Ticket ]  [ 📥 Agent Triage ] |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|                                [ ACTIVE SCREEN VIEW ]                             |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

- **Top Navigation Bar:**
  - Brand identity with live status indicator (Online / Mock Demo Mode).
  - Screen navigation links with active highlight bar.
  - **Demo State Switcher:** Global interactive control allowing operators and reviewers to toggle `Loading`, `Empty`, `Success`, and `Error` states instantly.
- **Mobile Drawer / Bottom Nav:** On small viewports (`< 768px`), navigation adapts to a compact header with collapsible menu or segmented tab bar.

---

## 4. Screen Specifications & Architecture

### 4.1 Screen 1: Customer AI Chat Assistant (RAG Interaction)
- **Purpose:** Provide immediate, citation-backed answers to customer questions with one-click fallback escalation.
- **Key UI Elements:**
  - **Quick Prompts / FAQ Pills:** Clickable chips for common questions (*"Password Reset", "Billing Cycle", "API Token"*).
  - **Conversation Timeline:**
    - User message bubbles (Right-aligned, indigo background).
    - Assistant message bubbles (Left-aligned, white card with subtle border).
    - **Citation Badge:** Clickable pill displaying source (*"Source: Doc #4 – Account Recovery"*).
    - **Feedback Actions:** "Helpful" / "Not helpful" icons for instant user feedback.
  - **Fallback Card:** Appears if AI confidence is low or error state is triggered:
    - *"AI was unable to resolve this with certainty. Review verified FAQ articles or escalate to a human specialist."*
    - Button: **[Escalate to Priority Ticket]** (pre-fills context into Screen 2).
  - **Chat Input Bar:** Text input with send button and character counter.

---

### 4.2 Screen 2: Submit / Escalate Ticket (Working Form with Validation)
- **Purpose:** Allow customers to submit a detailed support ticket with immediate client-side validation and feedback.
- **Form Layout:** Clean, centered 2-column or 1-column responsive card.
- **Field Specifications & Validation Rules:**

| Field Label | Input Type | Validation Rules | Error Message |
| :--- | :--- | :--- | :--- |
| **Full Name** | Text Input | Required, min 2 characters | *"Please enter your full name."* |
| **Customer Email**| Email Input | Required, RFC 5322 regex match | *"Please provide a valid email address."* |
| **Category** | Select Dropdown | Required, must select one valid option | *"Please select a support category."* |
| **Priority** | Radio / Pill Select| Required (`Low`, `Medium`, `High`, `Urgent`)| Default set to `Medium` |
| **Subject** | Text Input | Required, min 5 characters | *"Subject must be at least 5 characters."* |
| **Description** | Textarea (4 rows)| Required, min 15 characters | *"Please describe your issue (min 15 chars)."* |

- **Validation Behaviors:**
  - **Inline Feedback:** Red border (`border-rose-500`) and error text (`text-rose-600 text-xs`) appear immediately if a touched field is invalid upon submission or blur.
  - **Submission State:**
    1. Clicking "Submit Ticket" sets `isSubmitting = true` (disables button, shows spinner).
    2. Simulated network latency of 800ms.
    3. Triggers **Success State**: Displays a success card with generated ticket ID (e.g., `#TICK-1042`), estimated response time, and a button to view in the Agent Queue.

---

### 4.3 Screen 3: Support Agent Triage Dashboard
- **Purpose:** Allow support specialists to review incoming tickets, inspect auto-assigned AI tags, and review AI draft replies.
- **Split-Panel Layout (Desktop) / Stacked (Mobile):**
  - **Left Panel (Ticket Queue List):**
    - Search bar & filter dropdown (Category, Urgency).
    - Ticket list items showing Ticket ID, Title, Customer Name, Relative Time, and Status Badge.
    - AI Tag Pills: e.g., `[Authentication]`, `[Priority: Urgent]`.
  - **Right Panel (Ticket Detail & AI Copilot):**
    - Full customer issue message and history.
    - **AI Suggested Draft Box:**
      - Pre-populated draft resolution generated based on policy documents.
      - Editable textarea allowing the agent to customize before sending.
      - Action buttons: **[Approve & Send Draft]**, **[Reject / Write Manually]**.

---

## 5. Mock Data & 4 UI States Specification

To ensure high enterprise resilience and rigorous UX standards, the UI explicitly demonstrates four discrete operational states:

```
+-------------------------------------------------------------------------------+
| State Controller:  (o) Success (Normal)   ( ) Loading   ( ) Empty   ( ) Error |
+-------------------------------------------------------------------------------+
```

### 5.1 Loading State
- **Visuals:** Skeleton placeholders with animated pulses (`animate-pulse`) for ticket list items, message bubbles, and stats cards.
- **Purpose:** Communicates active data retrieval or AI token synthesis without UI freezing.

### 5.2 Empty State
- **Visuals:** Centered illustrated icon (`Inbox` / `CheckCircle2`), cheerful headline *"No Tickets in Queue"*, descriptive body *"All customer inquiries have been resolved. Good job!"*, and a *"Create Test Ticket"* action button.
- **Purpose:** Prevents confusing blank space when no items match filters.

### 5.3 Success State (Normal Operations)
- **Visuals:** Full rendering of interactive mock data:
  - 4-5 populated support tickets spanning different categories (`Billing`, `Bug`, `Authentication`).
  - Active chat thread with structured AI markdown and verified citation link.
  - Toast banner confirming successful operations.

### 5.4 Error / Outage State
- **Visuals:** Prominent alert banner with `rose-50` background, `rose-600` border, and alert icon:
  - Title: *"AI Inference Service Unavailable (Simulated Error 503)"*
  - Description: *"Failed to connect to the LLM orchestrator. Deterministic fallback mode is active."*
  - CTA Buttons: **[Retry Connection]** and **[Use Rule-Based FAQs]**.
- **Purpose:** Directly satisfies User Story 2 (Non-AI Fallback) by showing how the frontend gracefully guides the user rather than crashing.

---

## 6. Implementation Architecture & File Layout

For ease of maintainability, code cleanliness, and scalability, the UI skeleton is structured into modular components:

```text
src/
├── components/
│   ├── Navigation.tsx         # Top bar with screen switcher & demo controls
│   ├── ChatScreen.tsx         # Screen 1: Customer RAG chat & citations
│   ├── TicketFormScreen.tsx   # Screen 2: Form with client-side validation
│   ├── AgentDashboardScreen.tsx # Screen 3: Agent queue, details & AI draft reply
│   ├── StateController.tsx    # Demo switch for Loading/Empty/Success/Error
│   └── ui/                    # Reusable atomic UI (Button, Badge, Skeleton)
├── types/
│   └── index.ts               # Type definitions for Ticket, Message, FormState
└── App.tsx                    # Main layout combining screens & demo states
```

---

## 7. Human Review & Verification Checklist

| Criteria | Verification Step | Status |
| :--- | :--- | :--- |
| **Main Navigation** | Switch between Chat, Form, and Agent views seamlessly | Designed |
| **2-3 Essential Screens** | Customer Chat, Submit Ticket Form, Agent Dashboard | Designed |
| **Form with Validation** | Email regex, required fields, character limits, error messages | Designed |
| **4 UI States** | Dedicated toggles for Loading, Empty, Success, and Error | Designed |
| **Responsive Web Layout** | Flex/grid layouts with mobile collapsing breakpoints | Designed |
| **AI Generation Record** | Prompts and human review decisions logged in `AI_REVIEW_LOG.md` | Prepared |
