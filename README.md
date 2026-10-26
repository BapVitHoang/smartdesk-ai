# SmartDesk AI - Intelligent Customer Support & Knowledge Synthesizer

Nền tảng hỗ trợ khách hàng thông minh kết hợp trợ lý AI (RAG), cơ chế dự phòng không AI (Deterministic BM25 Fallback), thẩm định tri thức chủ động (Active Verification) và hệ thống phân loại, điều phối Ticket tự động (AI Copilot).

---

## 1. Thông tin Dự án

**SmartDesk AI** giải quyết 2 bài toán lớn trong vận hành chăm sóc khách hàng:
1. **Giảm tải cho đội ngũ hỗ trợ:** Tự động trả lời câu hỏi thường gặp, phân loại ticket, gán nhãn, xác định mức độ ưu tiên (SLA: `Urgent=2h, High=4h, Medium=8h, Low=24h`) và soạn sẵn bản thảo câu trả lời (`ai_draft_reply`).
2. **Loại bỏ tình trạng AI "ảo giác" (Hallucination):** Ứng dụng mô hình RAG (Retrieval-Augmented Generation) đối soát trực tiếp với cơ sở tri thức (Knowledge Base / FAQ), đồng thời trích dẫn nguồn tài liệu minh bạch (`[Doc #ID: Tiêu đề]`).

### Tính năng chính
- **AI Chatbot hỗ trợ RAG & Trích dẫn nguồn:** Tích hợp Dual AI Provider: Google Gemini (`gemini-3.5-flash-lite` với fallback sang `gemini-2.5-flash-lite`, thay thế `gemini-1.5-flash` đã ngừng cung cấp) hoặc Local Ollama (`qwen2.5:3b` + `nomic-embed-text`) để tổng hợp câu trả lời chính xác, kèm badge trích dẫn tài liệu tham chiếu.
- **Cơ chế Cost-Guard Circuit Breaker & Fallback BM25 (< 4.0s):** Nếu gọi API LLM bị timeout (> 4.0s), lỗi mạng hoặc chạm rate limit (HTTP 429), hệ thống tự động khóa gọi API ngoài trong 60s và kích hoạt bộ máy so khớp từ khóa BM25 cục bộ trên `seed_faq.json` mà không làm gián đoạn trải nghiệm người dùng.
- **Phân loại & Điều phối Ticket (Ticket Triage):** Tự động sinh mã ticket chuẩn định dạng `#TICK-XXXX`, gán nhãn danh mục (`Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General`), tính hạn xử lý SLA và gợi ý mức độ khẩn cấp.
- **AI Copilot cho Hỗ trợ viên:** Tự động soạn trước câu trả lời mẫu cho từng ticket để nhân viên hỗ trợ duyệt, chỉnh sửa hoặc gửi nhanh chóng.
- **Bảng điều khiển Quản trị (Agent Dashboard):** Giao diện quản lý ticket trực quan với các bộ lọc theo trạng thái, độ ưu tiên, danh mục và thanh tìm kiếm thời gian thực.
- **Quản trị Tri thức Đa Doanh nghiệp (Multi-Tenant) & Sát hạch AI (Active Verification):** Hỗ trợ nhiều Workspace độc lập (Y tế/Nha khoa, Bán lẻ công nghệ, IT SaaS), nạp tài liệu động (`.pdf`, `.txt`, `.md`), chạy kiểm định 3 bước (Synthetic QA -> RAG Test -> AI Judge) trước khi xuất bản.

### Công nghệ sử dụng (Tech Stack)
- **Frontend:** React 19, Vite 6, Tailwind CSS v4, TypeScript, Lucide Icons, Motion (SPA).
- **Backend:** Python 3.11+, FastAPI (100% Async ASGI), SQLAlchemy 2.0 (Async), PostgreSQL 16 (`pgvector`) / SQLite (`aiosqlite` fallback).
- **AI & Retrieval:** Google Gemini (`gemini-3.5-flash-lite`, `gemini-embedding-001`), Local Ollama (`qwen2.5:3b`, `nomic-embed-text`), Okapi BM25 Fallback Engine.

---

## 2. Cấu trúc Dự án

```text
smartdesk-ai/
├── frontend/                 # Mã nguồn Frontend (React 19 + Vite 6 + Tailwind CSS v4)
│   ├── src/
│   │   ├── components/       # Header, ChatView, TicketFormView, AgentDashboardView, KnowledgeManagerView, Footer
│   │   ├── features/         # Các module mở rộng tính năng độc lập
│   │   ├── services/         # Client kết nối API backend với cơ chế offline fallback (api.ts)
│   │   ├── App.tsx           # Điều phối giao diện và trạng thái chính
│   │   ├── data.ts           # Dữ liệu mẫu & cấu hình khởi tạo
│   │   └── types.ts          # Định nghĩa kiểu dữ liệu TypeScript (Frozen Contract)
│   ├── package.json
│   └── vite.config.ts
├── backend/                  # Mã nguồn Backend (FastAPI Async)
│   ├── app/
│   │   ├── api/v1/endpoints/ # API routes: chat, tickets, agent, knowledge, health, workspaces, documents
│   │   ├── core/             # Cấu hình (config.py), prompts (prompts.py), bảo mật (security.py), ngoại lệ (exceptions.py)
│   │   ├── db/               # Khởi tạo kết nối & session cơ sở dữ liệu (session.py)
│   │   ├── models/           # SQLAlchemy ORM Models (Ticket, FAQItem, KnowledgeChunk, Workspace, Document, Verification)
│   │   ├── schemas/          # Pydantic v2 schemas cho Request/Response
│   │   ├── services/         # Nghiệp vụ: LLM, Embedding, BM25 Fallback, RAG, Ticket Copilot, Document, Verification
│   │   └── main.py           # Điểm khởi chạy ứng dụng FastAPI & CORS
│   ├── data/
│   │   ├── sample_documents/ # Tài liệu mẫu thực tế cho các lĩnh vực (SmileCare, TechStore)
│   │   ├── prompts.json      # Kho lưu trữ System Prompts có đánh phiên bản
│   │   └── seed_faq.json     # 12 bài viết FAQ chuẩn cho Fallback & Seed dữ liệu
│   ├── scripts/              # Công cụ tiện ích (reembed_chunks.py, export_finetune_dataset.py)
│   ├── tests/                # Bộ kiểm thử tự động pytest (test_api, test_workspace_and_verification, test_ollama_provider, ...)
│   ├── .env.example          # Mẫu file cấu hình môi trường backend
│   ├── Dockerfile            # Cấu hình đóng gói Docker
│   └── requirements.txt      # Danh sách thư viện Python
├── docs/
│   ├── ARCHITECTURE.md       # Kiến trúc hệ thống & Phân quyền sở hữu thư mục (Module Ownership)
│   ├── API_CONTRACT.md       # Đặc tả chi tiết Request/Response của các API
│   ├── DESIGN.md             # Design tokens & đặc tả UI/UX
│   ├── TEST_ACCEPTANCE.md    # Kịch bản kiểm thử nghiệm thu (Acceptance Tests)
│   ├── PROPOSAL.md           # Đề xuất dự án, 12 User Stories & Ma trận truy vết (Traceability Matrix)
│   ├── adr/                  # Architecture Decision Records (ADR-001 .. ADR-004)
│   ├── audit/                # Báo cáo kiểm toán & phân tích khoảng cách (Gap Analysis)
│   ├── plan/                 # Kế hoạch thực thi (PLAN.md)
│   └── spec/                 # Đặc tả kỹ thuật chi tiết (SPEC.md)
├── scripts/
│   ├── start_all.bat         # Script khởi động đồng thời cả Frontend và Backend
│   ├── start_backend.bat     # Script khởi động riêng Backend FastAPI
│   ├── start.bat             # Script khởi động riêng Frontend Vite
│   └── install.bat           # Script cài đặt tự động cả Node.js và Python packages
├── AI_USAGE.md               # Nhật ký sử dụng AI, kiểm chứng và nghiên cứu tình huống sửa lỗi
├── AGENTS.md                 # Quy tắc kiến trúc và phối hợp bắt buộc cho AI Agents
├── docker-compose.yml        # Triển khai PostgreSQL 16 pgvector + Backend FastAPI
└── README.md                 # Tài liệu hướng dẫn tổng quan dự án
```

---

## 3. Cài đặt & Thiết lập Môi trường (Setup)

### Yêu cầu tiên quyết
- **Node.js:** Phiên bản 18+ và `npm`
- **Python:** Phiên bản 3.11+ và `pip`

### 3.1. Thiết lập Backend
1. Cài đặt các thư viện Python:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Tạo file cấu hình môi trường `.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```
3. Cấu hình các biến chính trong `backend/.env`:
   - `AI_PROVIDER`: `"gemini"` (mặc định) hoặc `"ollama"` (chạy mô hình cục bộ không tốn chi phí API).
   - `GEMINI_API_KEY`: Khóa API Google Gemini lấy từ [Google AI Studio](https://aistudio.google.com/). *(Nếu để trống, hệ thống sẽ tự động chuyển sang chế độ Fallback BM25)*.
   - `LLM_MODEL_NAME`: `"gemini-3.5-flash-lite"` (Mô hình LLM chuẩn; tự động fallback sang `"gemini-2.5-flash-lite"` nếu cần).
   - `EMBEDDING_MODEL_NAME`: `"gemini-embedding-001"` (Mô hình vector hóa).
   - `DATABASE_URL`: Mặc định sử dụng SQLite async `sqlite+aiosqlite:///./smartdesk.db` (hoặc PostgreSQL 16 `pgvector` khi dùng Docker).
   - `LLM_TIMEOUT_SECONDS`: `4.0` (Ngưỡng thời gian tối đa cho cuộc gọi AI trước khi kích hoạt Fallback).

### 3.2. Thiết lập Frontend
1. Cài đặt thư viện Frontend:
   ```bash
   npm install --prefix frontend
   ```
2. (Tùy chọn) Tạo file `frontend/.env.local` từ mẫu `frontend/.env.example`.

---

## 4. Cách chạy Dự án (How to Run)

### 4.1. Chạy nhanh trên Windows
- Cài đặt toàn bộ thư viện: `scripts\install.bat`
- Khởi động đồng thời Backend + Frontend: `scripts\start_all.bat`

### 4.2. Khởi chạy thủ công
- **Backend (cổng 8000):**
  ```bash
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Frontend (cổng 3000):**
  ```bash
  npm run dev --prefix frontend
  ```

### 4.3. Chạy bằng Docker Compose (bản dùng để demo)
Yêu cầu: Docker Desktop (Compose v2).

1. Tạo file `.env` ở **thư mục gốc** (cạnh `docker-compose.yml`) để Compose truyền biến vào container. Chỉ khai báo các biến cần thiết, ví dụ tên biến (không commit giá trị):
   ```dotenv
   GEMINI_API_KEY=
   JWT_SECRET_KEY=
   GOOGLE_OAUTH_CLIENT_ID=
   POSTGRES_PASSWORD=
   ```
2. Build và khởi động 3 dịch vụ (PostgreSQL 16 + pgvector, Backend FastAPI, Frontend Nginx):
   ```bash
   docker compose up --build -d
   ```
3. Truy cập:
   - Giao diện: <http://localhost:3000>
   - API & Swagger: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/v1/health>
4. Kiểm tra trạng thái và log: `docker compose ps` · `docker compose logs -f backend`
5. Dừng: `docker compose down` (dữ liệu PostgreSQL được giữ trong volume `pgdata`).

> Kiểm tra nhanh trên Windows: `powershell -ExecutionPolicy Bypass -File scripts/smoke_docker.ps1`.

### 4.4. Biến môi trường (chỉ liệt kê tên, không kèm giá trị)

| Biến | Nơi dùng | Bắt buộc | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `AI_PROVIDER` | Backend | Không | `gemini` (mặc định) hoặc `ollama` |
| `GEMINI_API_KEY` / `GEMINI_API_KEYS` | Backend | Không | Khóa Gemini; để trống thì hệ thống chạy chế độ dự phòng BM25 |
| `LLM_MODEL_NAME`, `LLM_FALLBACK_MODEL`, `LLM_FALLBACK_MODEL_NAME` | Backend | Không | Model chính và model dự phòng |
| `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIMENSIONS` | Backend | Không | Model và số chiều embedding |
| `LLM_TIMEOUT_SECONDS`, `RATE_LIMIT_COOLDOWN_SECONDS` | Backend | Không | Ngưỡng timeout và thời gian khóa Cost-Guard |
| `LLM_INPUT_COST_PER_MILLION`, `LLM_OUTPUT_COST_PER_MILLION` | Backend | Không | Đơn giá token để tính chi phí |
| `OLLAMA_BASE_URL`, `OLLAMA_LLM_MODEL`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_KEEP_ALIVE` | Backend | Khi dùng Ollama | Cấu hình model cục bộ |
| `DATABASE_URL`, `FALLBACK_SQLITE_URL` | Backend | Không | Kết nối PostgreSQL; tự chuyển sang SQLite khi không kết nối được |
| `POSTGRES_PASSWORD` | Docker Compose | Không | Mật khẩu PostgreSQL trong container |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | **Có** khi tắt demo login | Khóa ký và thời hạn JWT |
| `GOOGLE_OAUTH_CLIENT_ID` | Backend + Docker build frontend | Khi dùng đăng nhập Google | OAuth2 Web Client ID của Google |
| `VITE_GOOGLE_CLIENT_ID` | Frontend (`frontend/.env.local`) | Khi dùng đăng nhập Google | Cùng giá trị với `GOOGLE_OAUTH_CLIENT_ID`; để trống thì ẩn nút Google |
| `VITE_API_URL` | Frontend | Không | URL API backend |
| `DEMO_LOGIN_ENABLED`, `DEMO_ADMIN_PASSWORD`, `DEMO_USER_PASSWORD`, `ADMIN_EMAILS` | Backend | Không | Tài khoản demo và danh sách email admin |
| `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_THROTTLE_WINDOW_SECONDS` | Backend | Không | Chống dò mật khẩu |
| `CORS_ORIGINS` | Backend | Không | Danh sách origin được phép |
| `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RAG_CONFIDENCE_THRESHOLD`, `RAG_MIN_SIMILARITY_SCORE` | Backend | Không | Tham số RAG |
| `PROMPTS_PATH`, `SEED_FAQ_PATH` | Backend | Không | Đường dẫn catalog prompt và FAQ |

Danh sách đầy đủ có mô tả nằm trong `backend/.env.example` và `frontend/.env.example`.

---

## 5. Kiểm thử Hệ thống (Testing)

```bash
# Kiểm thử Backend (Pytest)
pytest backend/tests/ -v

# Kiểm tra kiểu dữ liệu TypeScript & Build Frontend
npm run lint --prefix frontend
npm run build --prefix frontend
```

---

## 6. Thành viên Nhóm & Phân công Module (Team Roster & Ownership — REQ-29)

SmartDesk AI được phát triển bởi **nhóm 3 thành viên** (Dev B kiêm nhiệm vai trò Integrator điều phối kiến trúc và release).

Họ tên và MSSV: xem docs/TEAM_ROSTER.md.

| Định danh (Identifier) | GitHub | Vai trò chính | Phân công Module & Quyền sở hữu (REQ-29) |
| :--- | :--- | :--- | :--- |
| **Dev B & Integrator** | [`@BapVitHoang`](https://github.com/BapVitHoang) | **Dev B & Integrator** | Platform, Database, OAuth2/JWT, Ticket CRUD, Docker Compose, Frozen Governance & Release |
| **Dev A** | [`@TheOrijinnn`](https://github.com/TheOrijinnn) | **Dev A** | AI Engine, RAG Pipeline, Single-call Structured Output, Tool-using Agent, 24-case Eval Benchmark |
| **Dev C** | [`@TKhanh`](https://github.com/TKhanh) | **Dev C** | Frontend UX, Streaming Bubble, Confirmation UI, Telemetry View, Integration Tests & Capstone Docs |

---

## 7. Tài khoản Kiểm thử (Test Accounts)

Hệ thống tích hợp sẵn cơ chế đăng nhập một chạm (1-click Demo Switcher) trên thanh điều hướng Header:

| Email | Vai trò (Role) | Quyền hạn truy cập | Ghi chú |
| :--- | :--- | :--- | :--- |
| `admin@smartdesk.ai` | `admin` | **Toàn quyền:** Chat RAG, Form ticket, Bảng điều khiển Agent Copilot, Quản lý Tri thức & Báo cáo Telemetry. | Đăng nhập 1-click qua nút "Demo Admin" |
| `an.nguyen@company.vn` | `user` | **Giới hạn Khách hàng:** Hỏi đáp Chatbot, Gửi ticket, xem ticket cá nhân (Khóa/ẩn 2 tab quản trị Agent & Tri thức). | Đăng nhập 1-click qua nút "Demo User" |

---

## 8. Chính sách Quyền riêng tư Dữ liệu AI (Data Privacy & PII Masking Policy)

- **Mặt nạ dữ liệu cá nhân (`redact_pii`):** Toàn bộ địa chỉ email, số điện thoại Việt Nam và số Căn cước công dân/CMND trong tin nhắn của người dùng đều được tự động ẩn danh hóa thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_ID]` trước khi truyền tải đến Google Gemini API hoặc các mô hình nhúng (Embedding).
- **Hàng rào an toàn Prompt Injection (`check_prompt_injection`):** Mọi truy vấn độc hại bằng tiếng Anh hoặc tiếng Việt tìm cách thay đổi chỉ thị hệ thống bị chặn ngay tại tầng API Gateway với mã HTTP 400 (`PROMPT_SECURITY_VIOLATION`), không tốn token và không đưa dữ liệu nguy hại vào bộ nhớ đệm.
- **Không lưu trữ bí mật:** Token JWT HS256 có thời hạn và khóa phiên làm việc nghiêm ngặt, dữ liệu khách hàng được cô lập theo `customer_email`.

