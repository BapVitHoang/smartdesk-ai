# Developer B — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

## Out-of-Scope Security & Hardening Requests
REQ-SEC-01 | backend/app/db/seed/seed_users.py | Demo accounts are seeded with default passwords even when DEMO_LOGIN_ENABLED=false; guard seed and login with DEMO_LOGIN_ENABLED check | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-02 | backend/Dockerfile | Uvicorn launched without --proxy-headers / --forwarded-allow-ips, collapsing client IPs behind Nginx reverse proxy | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-03 | backend/app/api/v1/endpoints/tickets.py | POST /api/v1/tickets is unauthenticated and calls Gemini Copilot without rate limiting | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-04 | backend/app/api/v1/endpoints/tickets.py | In list_tickets(), normalize category alias: if category and category.strip() == "Technical Bug": category = "Bug Report" per AGENTS.md contract | devB | LEFT FOR OWNER

## Change Requests for Dev C (Frontend UX & Mocks)
CR-DEVC-01 | frontend/src/services/api/tickets.ts | In createTicket(), attach getAuthHeaders() to headers to support authenticated ticket creation (POST /api/v1/tickets now requires Bearer auth per REQ-SEC-03) and prompt unauthenticated visitors to log in | devC | DONE: feat(ux): support authenticated ticket creation and 43 demo tickets pagination (CR-DEVC-01, CR-DEVC-02)
CR-DEVC-02 | frontend/src/services/api/tickets.ts | 40 deterministic demo tickets plus 3 initial tickets (total exactly 43 tickets) are seeded in Docker PostgreSQL supporting pagination (?page=2) and sorting. On a fresh volume, admin sees all 43 tickets; An Nguyen sees exactly 15 tickets (1 initial #TICK-1042 + 14 demo #TICK-1101..1114). The previous count of 26 in persisted container was due to 11 accumulated test tickets. To reset demo data to this verified state: run `docker compose down -v && docker compose up -d` | devC | DONE: feat(ux): support authenticated ticket creation and 43 demo tickets pagination (CR-DEVC-01, CR-DEVC-02) + chore(requests): apply CR-DEVC-02
CR-DEVC-03 | README.md | In Section 4 (Cách chạy Dự án), add explicit subsection 4.3 for Docker Compose startup via `docker compose up --build` per REQ-39 | devC | LEFT FOR OWNER

## Post-Merge Integration Audit Requests (Prompt M)
MRG-DEF-01 | docs/SLIDES.pdf, docs/SLIDES.pptx | check_roster.py reports 15 fabrication violations in extracted slide text (already tracked under CR-002; binaries taken from origin/feature/c-frontend-docs per Policy P5 to be regenerated in Prompt 5) | devC
MRG-DEF-02 | docs/notes/A-ai-usage.md, scripts/check_roster.py | Line 51 `- **AI Tool Used:** Google Antigravity Coding Assistant` followed by role tag triggers check_roster.py NAME_ROLE_PATTERN false positive | devA / integrator
MRG-DEF-03 | frontend/src/services/api/tickets.ts | updateTicketStatus() (line 337) and regenerateAiDraft() (line 417) omit getAuthHeaders(), causing HTTP 401 against admin-protected PATCH /api/v1/tickets/{id} and POST /api/v1/agent/tickets/{id}/generate-draft | devC
MRG-DEF-04 | frontend/src/services/api/documents.ts | uploadDocument() (line 159), deleteDocument() (line 203), verifyDocument() (line 232), and publishDocument() (line 288) omit getAuthHeaders(), causing HTTP 401 against admin-protected document endpoints | devC
MRG-DEF-05 | frontend/src/services/api/workspaces.ts | createWorkspace() (line 35) and updateWorkspace() (line 75) omit getAuthHeaders(), causing HTTP 401 against admin-protected workspace endpoints | devC
MRG-DEF-06 | backend/app/services/agent_tools.py | handle_prepare_ticket_update() (line 467) does not record creator_id/creator_email on PendingAction and execute_pending_action() (line 234) updates ticket status/priority without verifying non-admin ticket ownership | devA
MRG-DEF-07 | backend/app/services/rag_service.py, backend/app/services/ticket_copilot_service.py | log_ai_call() is invoked with status="config_error" (rag_service.py:448, ticket_copilot_service.py:186), whereas CONTRACTS.md §2 specifies Literal["success", "fallback", "refused"] | devA / integrator
MRG-DEF-08 | frontend/src/services/api/documents.ts, docs/spec/CONTRACTS.md | getVerificationReport() (documents.ts:265) calls GET /api/v1/documents/{id}/verification-report (matching endpoints/documents.py:181), whereas CONTRACTS.md §8.12 header lists GET /api/v1/documents/{id}/verify | integrator
MRG-DEF-09 | frontend/src/services/api/tickets.ts | getTickets() (line 231) defaults limit to 50 instead of CONTRACTS.md §8.10 default 20 and does not expose X-Total-Count response header to caller | devC


