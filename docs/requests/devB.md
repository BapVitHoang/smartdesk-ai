# Developer B — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

## Out-of-Scope Security & Hardening Requests
REQ-SEC-01 | backend/app/db/seed/seed_users.py | Demo accounts are seeded with default passwords even when DEMO_LOGIN_ENABLED=false; guard seed and login with DEMO_LOGIN_ENABLED check | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-02 | backend/Dockerfile | Uvicorn launched without --proxy-headers / --forwarded-allow-ips, collapsing client IPs behind Nginx reverse proxy | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-03 | backend/app/api/v1/endpoints/tickets.py | POST /api/v1/tickets is unauthenticated and calls Gemini Copilot without rate limiting | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation

## Change Requests for Dev C (Frontend UX & Mocks)
CR-DEVC-01 | frontend/src/services/api/tickets.ts | In createTicket(), attach getAuthHeaders() to headers to support authenticated ticket creation (POST /api/v1/tickets now requires Bearer auth per REQ-SEC-03) and prompt unauthenticated visitors to log in | devC
CR-DEVC-02 | frontend/src/services/api/tickets.ts | 40+ deterministic demo tickets (total 43) are now seeded in Docker PostgreSQL supporting pagination (?page=2) and sorting. Admin sees all 43 tickets; An Nguyen sees isolated tickets (15 tickets in fresh seed, 26 in persisted container). To reset demo data for clean UI testing: run `docker compose down -v` then `docker compose up -d` | devC

