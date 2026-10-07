# SmartDesk AI - Intelligent Customer Support & Knowledge Synthesizer

Nền tảng hỗ trợ khách hàng thông minh kết hợp trợ lý AI (RAG), cơ chế dự phòng không AI (Deterministic Fallback) và hệ thống phân loại, điều phối Ticket tự động (AI Copilot).

---

## 1. Thông tin Dự án

**SmartDesk AI** giải quyết 2 bài toán lớn trong vận hành chăm sóc khách hàng:
1. **Giảm tải cho đội ngũ hỗ trợ:** Tự động trả lời câu hỏi thường gặp, phân loại ticket, gán nhãn, xác định mức độ ưu tiên và soạn sẵn bản thảo câu trả lời (AI draft reply).
2. **Loại bỏ tình trạng AI "ảo giác" (Hallucination):** Ứng dụng mô hình RAG (Retrieval-Augmented Generation) đối soát trực tiếp với cơ sở tri thức (Knowledge Base / FAQ), đồng thời trích dẫn nguồn tài liệu minh bạch (`[Doc #ID: Tiêu đề]`).

### Tính năng chính
- **AI Chatbot hỗ trợ RAG & Trích dẫn nguồn:** Tích hợp Google Gemini (`gemini-3.5-flash-lite` - thế hệ mới nhất thay thế `gemini-1.5-flash` đã ngừng cung cấp) để tổng hợp câu trả lời chính xác, kèm badge trích dẫn tài liệu tham chiếu.
- **Cơ chế Circuit Breaker & Fallback BM25 (< 4.0s):** Nếu gọi API LLM bị timeout (> 4.0s), lỗi mạng hoặc chạm rate limit (429), hệ thống tự động kích hoạt bộ máy so khớp từ khóa BM25 cục bộ trên `seed_faq.json` mà không làm gián đoạn trải nghiệm người dùng.
- **Phân loại & Điều phối Ticket (Ticket Triage):** Tự động sinh mã ticket chuẩn định dạng `#TICK-XXXX`, gán nhãn danh mục, tính hạn xử lý SLA và gợi ý mức độ khẩn cấp.
- **AI Copilot cho Hỗ trợ viên:** Tự động soạn trước câu trả lời mẫu cho từng ticket để nhân viên hỗ trợ duyệt, chỉnh sửa hoặc gửi nhanh chóng.
- **Bảng điều khiển Quản trị (Agent Dashboard):** Giao diện quản lý ticket trực quan với các bộ lọc theo trạng thái, độ ưu tiên, danh mục và thanh tìm kiếm thời gian thực.
- **Quản trị Tri thức Đa Doanh nghiệp (Multi-Tenant) & Sát hạch AI (Active Verification):** Hỗ trợ nhiều Workspace độc lập (Y tế/Nha khoa, Bán lẻ công nghệ, IT SaaS), nạp tài liệu động (.pdf, .txt, .md), chạy kiểm định 3 bước (Synthetic QA -> RAG Test -> AI Judge) trước khi xuất bản.

### Công nghệ sử dụng (Tech Stack)
- **Frontend:** React 19, Vite, Tailwind CSS v4, Lucide Icons, Motion.
- **Backend:** Python 3.11+, FastAPI (100% Async ASGI), SQLAlchemy 2.0 (Async), SQLite / PostgreSQL (hỗ trợ `pgvector`).
- **AI & Retrieval:** Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`), Embedding model (`gemini-embedding-001`), BM25 Fallback Engine.

---

## 2. Cấu trúc Dự án

```text
smartdesk-ai/
├── src/                      # Mã nguồn Frontend (React + Vite)
│   ├── components/           # Header, ChatView, TicketFormView, AgentDashboardView, KnowledgeManagerView, Footer
│   ├── services/             # Client kết nối API backend với cơ chế offline fallback (api.ts)
│   ├── App.tsx               # Điều phối giao diện và trạng thái chính
│   ├── data.ts               # Dữ liệu mẫu & cấu hình khởi tạo
│   └── types.ts              # Định nghĩa kiểu dữ liệu TypeScript
├── backend/                  # Mã nguồn Backend (FastAPI Async)
│   ├── app/
│   │   ├── api/v1/endpoints/ # API routes: chat, tickets, agent, knowledge, health, workspaces, documents
│   │   ├── core/             # Cấu hình (config.py), bảo mật (security.py), xử lý ngoại lệ (exceptions.py)
│   │   ├── db/               # Khởi tạo kết nối & session cơ sở dữ liệu (session.py)
│   │   ├── models/           # SQLAlchemy ORM Models (Ticket, FAQItem, KnowledgeChunk, Workspace, Document, Verification)
│   │   ├── schemas/          # Pydantic v2 schemas cho Request/Response
│   │   ├── services/         # Nghiệp vụ: LLM, BM25 Fallback, RAG, Ticket Copilot, Document Ingestion, Verification
│   │   └── main.py           # Điểm khởi chạy ứng dụng FastAPI & CORS
│   ├── data/
│   │   ├── sample_documents/ # Tài liệu mẫu thực tế cho các lĩnh vực (SmileCare, TechStore)
│   │   └── seed_faq.json     # 12 bài viết FAQ chuẩn cho Fallback & Seed dữ liệu
│   ├── tests/
│   │   ├── test_api.py       # Bộ kiểm thử tự động pytest (httpx.AsyncClient)
│   │   └── test_workspace_and_verification.py # Bộ kiểm thử Workspaces, Ingestion & Verification
│   ├── .env.example          # Mẫu file cấu hình môi trường backend
│   ├── Dockerfile            # Cấu hình đóng gói Docker
│   └── requirements.txt      # Danh sách thư viện Python
├── docker-compose.yml        # Triển khai PostgreSQL 16 pgvector + Backend FastAPI
├── start_all.bat             # Script khởi động đồng thời cả Frontend và Backend
├── start_backend.bat         # Script khởi động riêng Backend FastAPI
├── start.bat                 # Script khởi động riêng Frontend Vite
├── install.bat               # Script cài đặt tự động cả Node.js và Python packages
├── API_CONTRACT.md           # Đặc tả chi tiết Request/Response của các API
├── TEST_ACCEPTANCE.md        # Kịch bản kiểm thử nghiệm thu (Acceptance Tests)
└── README.md                 # Tài liệu hướng dẫn tổng quan dự án
```

---

## 3. Cài đặt & Thiết lập Môi trường (Setup)

### Yêu cầu tiên quyết
- **Node.js:** Phiên bản 18+ và `npm`
- **Python:** Phiên bản 3.11+ và `pip`

### 3.1. Thiết lập Backend
1. Di chuyển vào thư mục backend:
   ```bash
   cd backend
   ```
2. Cài đặt các thư viện Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Tạo file cấu hình môi trường `.env`:
   ```bash
   cp .env.example .env
   ```
4. Cấu hình các biến chính trong `backend/.env`:
   - `GEMINI_API_KEY`: Khóa API Google Gemini lấy từ [Google AI Studio](https://aistudio.google.com/). *(Nếu để trống, hệ thống sẽ tự động chuyển sang chế độ Fallback BM25)*.
   - `LLM_MODEL_NAME`: `"gemini-3.5-flash-lite"` (Mô hình LLM chuẩn; thế hệ 1.5 đã ngừng hoạt động).
   - `EMBEDDING_MODEL_NAME`: `"gemini-embedding-001"` (Mô hình vector hóa; thay thế `text-embedding-004`).
   - `DATABASE_URL`: Mặc định sử dụng SQLite async `sqlite+aiosqlite:///./smartdesk.db` (chạy ngay không cần cài thêm DB server).
   - `LLM_TIMEOUT_SECONDS`: `4.0` (Ngưỡng thời gian tối đa cho cuộc gọi AI trước khi kích hoạt Fallback).
   - `CORS_ORIGINS`: `["http://localhost:3000","http://localhost:5173"]`.

### 3.2. Thiết lập Frontend
1. Mở terminal tại thư mục gốc dự án (`smartdesk-ai`):
   ```bash
   npm install
   ```
2. (Tùy chọn) Tạo file `.env.local` nếu cần tuỳ biến cấu hình phía client:
   ```bash
   cp .env.example .env.local
   ```

---

## 4. Cách chạy Dự án (How to Run)

Để hệ thống hoạt động đầy đủ, cần khởi chạy cả Backend và Frontend:

### 4.1. Khởi chạy Backend (FastAPI)
Tại thư mục `backend`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Base URL:** `http://localhost:8000/api/v1`
- **Tài liệu Swagger UI tương tác:** `http://localhost:8000/docs`
- **Kiểm tra trạng thái (Health Check):** `http://localhost:8000/api/v1/health`

### 4.2. Khởi chạy Frontend (Vite + React)
Tại thư mục gốc dự án (`smartdesk-ai`):
```bash
npm run dev
```
- Truy cập giao diện ứng dụng tại: `http://localhost:3000`

---

## 5. Kiểm thử Hệ thống (Testing)

Chạy bộ kiểm thử tự động của backend:
```bash
cd backend
pytest tests/ -v
```
Bộ test bao gồm:
- Kiểm tra trạng thái hệ thống (`health_check`, `smoke-test` đo độ trễ LLM).
- Trò chuyện RAG kèm trích dẫn nguồn và cơ chế Fallback Circuit Breaker.
- Lọc bảo vệ chống tấn công tiêm nhiễm câu lệnh (Prompt Injection Guardrails).
- Tạo ticket, sinh mã `#TICK-XXXX`, gán thẻ tự động và tính SLA.
- Chỉnh sửa và tái sinh bản thảo câu trả lời AI cho hỗ trợ viên.

---

## 6. Các lưu ý quan trọng (Important Notes)

1. **Khóa API Gemini (`GEMINI_API_KEY`) & Mô hình thế hệ mới:**
   - Hệ thống vận hành trên Google Gemini (`gemini-3.5-flash-lite`) và embedding (`gemini-embedding-001`). Thử nghiệm trực tiếp cho độ trễ tổng hợp **~922 ms** và độ trễ vector hóa **~491 ms** (đáp ứng tiêu chuẩn phản hồi thời gian thực < 1.5s).
   - Không bắt buộc API key để khởi động: khi không có key hoặc gặp sự cố mạng/rate limit, hệ thống kích hoạt **BM25 Deterministic Fallback** dựa trên `seed_faq.json` và trả về cờ `"is_fallback": true`.
2. **Cơ sở dữ liệu & Hành vi Docker / PostgreSQL:**
   - **Mặc định:** Sử dụng SQLite bất đồng bộ (`smartdesk.db`) để chạy cục bộ tức thì mà không cần cài đặt hoặc bật Docker.
   - **Môi trường Docker Compose:** Khi khởi động `docker-compose up`, hệ thống kết nối PostgreSQL 16 (`pgvector/pgvector:pg16`). Nếu Docker daemon chưa bật hoặc kết nối PostgreSQL bị gián đoạn, backend tự động kích hoạt cơ chế dự phòng chuyển tiếp sang SQLite cục bộ mà không làm sập ứng dụng.
3. **Cổng dịch vụ & CORS:**
   - Frontend mặc định chạy ở cổng `3000`, Backend chạy ở cổng `8000`.
   - Nếu bạn thay đổi cổng của một trong hai bên, hãy cập nhật lại biến `CORS_ORIGINS` trong `backend/.env`.
4. **Quy chuẩn mã Ticket:**
   - Tất cả mã ticket được hệ thống sinh tự động theo định dạng `#TICK-XXXX` (ví dụ: `#TICK-1001`).
   - Mức độ ưu tiên gồm 4 cấp: `Low`, `Medium`, `High`, `Urgent`.
