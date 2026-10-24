# Developer B — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

## Out-of-Scope Security & Hardening Requests
REQ-SEC-01 | backend/app/db/seed/seed_users.py | Demo accounts are seeded with default passwords even when DEMO_LOGIN_ENABLED=false; guard seed and login with DEMO_LOGIN_ENABLED check | devB
REQ-SEC-02 | backend/Dockerfile | Uvicorn launched without --proxy-headers / --forwarded-allow-ips, collapsing client IPs behind Nginx reverse proxy | devB
REQ-SEC-03 | backend/app/api/v1/endpoints/tickets.py | POST /api/v1/tickets is unauthenticated and calls Gemini Copilot without rate limiting | devB

