# Developer B — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

## Out-of-Scope Security & Hardening Requests
REQ-SEC-01 | backend/app/db/seed/seed_users.py | Demo accounts are seeded with default passwords even when DEMO_LOGIN_ENABLED=false; guard seed and login with DEMO_LOGIN_ENABLED check | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-02 | backend/Dockerfile | Uvicorn launched without --proxy-headers / --forwarded-allow-ips, collapsing client IPs behind Nginx reverse proxy | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation
REQ-SEC-03 | backend/app/api/v1/endpoints/tickets.py | POST /api/v1/tickets is unauthenticated and calls Gemini Copilot without rate limiting | devB | DONE: fix(security): enforce demo account restrictions, trusted proxy IP, and authenticated ticket creation

## Change Requests for Dev C (Frontend UX & Mocks)
CR-DEVC-01 | frontend/src/services/api/tickets.ts | In createTicket(), attach getAuthHeaders() to headers to support authenticated ticket creation (POST /api/v1/tickets now requires Bearer auth per REQ-SEC-03) and prompt unauthenticated visitors to log in | devC
CR-DEVC-02 | frontend/src/services/api/tickets.ts | 40 deterministic demo tickets plus 3 initial tickets (total exactly 43 tickets) are seeded in Docker PostgreSQL supporting pagination (?page=2) and sorting. On a fresh volume, admin sees all 43 tickets; An Nguyen sees exactly 15 tickets (1 initial #TICK-1042 + 14 demo #TICK-1101..1114). The previous count of 26 in persisted container was due to 11 accumulated test tickets. To reset demo data to this verified state: run `docker compose down -v && docker compose up -d` | devC

