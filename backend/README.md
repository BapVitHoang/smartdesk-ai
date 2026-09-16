# SmartDesk AI - Backend Service

Dịch vụ Backend bất đồng bộ (ASGI) xây dựng bằng **FastAPI**, cung cấp API cho trợ lý AI hỗ trợ khách hàng (RAG), điều phối ticket tự động và cơ chế dự phòng tìm kiếm từ khóa (BM25 Fallback).

---

## 1. Thông tin Dịch vụ

### Các tính năng cốt lõi:
- **Retrieval-Augmented Generation (RAG):** Sử dụng Google Gemini 1.5 Flash để tổng hợp câu trả lời dựa trên cơ sở tri thức, có trích dẫn tài liệu tham khảo (`[Doc #ID: Tiêu đề]`).
- **Circuit Breaker & Fallback BM25 (< 4.0s):** Tự động chuyển đổi sang tìm kiếm từ khóa/BM25 trên tập dữ liệu `data/seed_faq.json` khi LLM quá hạn (timeout), gặp lỗi 429 hoặc không có API key.
- **AI Copilot & Ticket Triage:** Tự động sinh mã `#TICK-XXXX`, gán thẻ phân loại, xác định độ ưu tiên, tính toán thời hạn SLA và tạo bản thảo phản hồi khách hàng.
- **Hỗ trợ Cơ sở dữ liệu linh hoạt:** Mặc định chạy SQLite Async (`aiosqlite`) cho môi trường phát triển cục bộ và hỗ trợ PostgreSQL (`asyncpg` + `pgvector`) cho môi trường triển khai thực tế.

---

## 2. Cấu trúc Thư mục

```text
backend/
├── app/
│   ├── api/v1/endpoints/   # Các REST endpoints (chat, tickets, agent, health)
│   ├── core/               # Cấu hình hệ thống, bảo mật (guardrails), xử lý lỗi
│   ├── db/                 # Khởi tạo kết nối & session cơ sở dữ liệu bất đồng bộ
│   ├── models/             # SQLAlchemy 2.0 ORM models (Ticket, FAQItem, KnowledgeChunk)
│   ├── schemas/            # Pydantic v2 schemas chuẩn hóa Request/Response
│   ├── services/           # Logic nghiệp vụ (LLM, BM25 Fallback, RAG, Ticket Copilot)
│   └── main.py             # Điểm khởi tạo ứng dụng FastAPI, cấu hình CORS
├── data/
│   └── seed_faq.json       # Dữ liệu FAQ mẫu phục vụ Fallback & Seed database
├── tests/
│   └── test_api.py         # Bộ kiểm thử tích hợp tự động (pytest + httpx)
├── .env.example            # Mẫu file biến môi trường
├── Dockerfile              # Cấu hình container Docker
└── requirements.txt        # Danh sách thư viện phụ thuộc
```

---

## 3. Cài đặt & Cấu hình (Setup)

### Bước 1: Cài đặt thư viện phụ thuộc
Yêu cầu: **Python 3.11+**
```bash
cd backend
pip install -r requirements.txt
```

### Bước 2: Thiết lập file môi trường `.env`
Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```

Các thông số cấu hình chính trong `.env`:
- `GEMINI_API_KEY`: Khóa API Google Gemini lấy từ [Google AI Studio](https://aistudio.google.com/). *(Tùy chọn: Nếu không điền, hệ thống sẽ tự động chuyển sang dùng Fallback BM25)*.
- `DATABASE_URL`: Đường dẫn kết nối CSDL, mặc định `sqlite+aiosqlite:///./smartdesk.db`.
- `LLM_TIMEOUT_SECONDS`: `4.0` (Thời gian chờ tối đa cho các lệnh gọi LLM).
- `CORS_ORIGINS`: Danh sách các domain Frontend được phép truy cập (ví dụ: `["http://localhost:3000","http://localhost:5173"]`).

---

## 4. Cách chạy Backend (How to Run)

Khởi động server phát triển bằng Uvicorn với chế độ tự động tải lại (hot reload):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Sau khi khởi động thành công:
- **API Base URL:** `http://localhost:8000/api/v1`
- **Tài liệu Swagger UI:** `http://localhost:8000/docs`
- **Tài liệu ReDoc:** `http://localhost:8000/redoc`
- **Health Check Endpoint:** `http://localhost:8000/api/v1/health`

---

## 5. Danh sách API Endpoints Chính

| Phương thức | Đường dẫn | Chức năng |
| :--- | :--- | :--- |
| `POST` | `/api/v1/chat` | Chatbot hỗ trợ khách hàng với RAG, trích dẫn tài liệu & Circuit Breaker |
| `POST` | `/api/v1/tickets` | Gửi ticket mới (tự sinh mã `#TICK-XXXX`, gán tag và sinh bản thảo trả lời) |
| `GET` | `/api/v1/tickets` | Lấy danh sách ticket (hỗ trợ lọc theo `status`, `category`, `priority`, `search`) |
| `GET` | `/api/v1/tickets/{id}` | Lấy chi tiết ticket theo ID hoặc mã định danh |
| `PATCH` | `/api/v1/tickets/{id}` | Cập nhật trạng thái ticket hoặc chỉnh sửa bản thảo câu trả lời |
| `POST` | `/api/v1/agent/tickets/{id}/generate-draft` | AI Copilot tái sinh bản thảo câu trả lời cho ticket |
| `GET` | `/api/v1/health` | Kiểm tra trạng thái hoạt động của dịch vụ và kết nối cơ sở dữ liệu |
| `GET` | `/api/v1/health/smoke-test` | Đo lường độ trễ thực tế của kết nối LLM |

---

## 6. Chạy Kiểm thử Tự động (Testing)

Thực thi bộ test tự động sử dụng `pytest`:
```bash
pytest tests/ -v
```
Tất cả các bài kiểm tra chạy độc lập trên cơ sở dữ liệu SQLite in-memory/tạm thời, kiểm thử toàn diện các luồng:
- Health check & Smoke test đo độ trễ.
- Chat RAG và cơ chế Circuit Breaker Fallback khi LLM timeout/lỗi.
- Bộ lọc ngăn chặn tấn công tiêm câu lệnh (Prompt Injection).
- Nghiệp vụ CRUD ticket, gán nhãn tự động và sinh bản thảo trả lời của AI Copilot.

---

## 7. Các lưu ý quan trọng (Important Notes)

1. **Nguyên tắc Bất đồng bộ (Async First):** Toàn bộ I/O bao gồm gọi database, gọi external API và đọc ghi file đều bắt buộc sử dụng `async` / `await` để tránh làm tắc nghẽn ASGI event loop.
2. **Cơ chế Circuit Breaker:** Khi thời gian phản hồi của Gemini vượt quá `LLM_TIMEOUT_SECONDS` (mặc định 4.0s) hoặc API trả về lỗi (429/500), dịch vụ sẽ tự động chuyển sang cơ chế Fallback BM25 và trả về cờ `"is_fallback": true`, không để xảy ra lỗi 500 cho người dùng.
3. **Định dạng Ticket & Mức độ Ưu tiên:**
   - Mã định danh bắt buộc theo định dạng: `#TICK-XXXX`.
   - Mức độ ưu tiên gồm đúng 4 cấp độ: `Low`, `Medium`, `High`, `Urgent`.
   - Vòng đời trạng thái ticket: `open` -> `in_progress` -> `resolved` (hoặc `closed`).
