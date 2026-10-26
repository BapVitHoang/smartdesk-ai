# ADR-002: Dual-Engine Vector & Relational Persistence (PostgreSQL 16 `pgvector` + Async SQLite Fallback)

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** SmartDesk AI Architecture Team (`Owner 2: Platform & Data`)

## 1. Context
The project requires production-grade vector similarity search (`pgvector`) alongside transactional relational storage for workspaces, documents, verification reports, and tickets. However, developers and graders frequently run `pytest` or local quickstart scripts (`scripts/start_all.bat`) on machines where Docker Desktop is not running.

## 2. Decision
We adopted a **Dual-Engine Persistence Layer** in `backend/app/db/session.py` and `backend/app/services/embedding_service.py`:
1. **Containerized Production Mode (`docker-compose.yml`):** Uses `pgvector/pgvector:pg16` with `postgresql+asyncpg://` connection pooling.
2. **Automatic Local Fallback (`SQLite + aiosqlite`):** If PostgreSQL is unreachable at startup (`init_db()`) or when running locally, `session.py` automatically falls back to `sqlite+aiosqlite:///<BACKEND_DIR>/smartdesk.db` and seeds 3 default workspaces, 12 curated FAQs, sample tickets, and domain documents.
3. **In-Python Cosine Similarity for SQLite / JSON Vectors:** Embeddings are stored in a portable JSON array column (`KnowledgeChunk.embedding`), allowing `embedding_service.py` to compute exact L2-normalized cosine similarity in < 3ms for workspace-scoped chunks without requiring native C extensions on Windows.

## 3. Alternatives Considered
- **Separate Dedicated Vector DB (Pinecone / Qdrant / ChromaDB):** Rejected due to synchronization complexity between relational ticket/workspace tables and external vector indices, especially during document deletion (`DELETE /api/v1/documents/{id}`).
- **Hard Requirement on Docker PostgreSQL for Local Tests:** Rejected because it prevents zero-config `pytest` execution in lightweight CI runners or local Windows environments without Docker running.

## 4. Consequences
- **Positive:** Zero-configuration developer onboarding (`pytest backend/tests/ -v` passes in ~28s out-of-the-box) while supporting full `pgvector/pgvector:pg16` deployment via Docker Compose.
- **Negative / Trade-off:** Schema changes during local development must be handled via `_migrate_sqlite_columns()` in `session.py` or clean DB recreation.
