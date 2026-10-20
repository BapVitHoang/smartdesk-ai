# SmartDesk AI - Giải Thích Chi Tiết Toàn Bộ File Mã Nguồn Python (.py)

Tài liệu này cung cấp cái nhìn chi tiết và dễ hiểu nhất về từng file mã nguồn Python (`.py`) trong thư mục `backend/` của dự án **SmartDesk AI**.

---

## 1. Sơ Đồ Cấu Trúc File Backend

```text
backend/
├── app/
│   ├── main.py                     # Điểm khởi chạy ứng dụng FastAPI & Cấu hình Middleware
│   ├── api/
│   │   └── v1/
│   │       ├── api.py              # Router tổng hợp các API v1
│   │       └── endpoints/
│   │           ├── chat.py         # Endpoint xử lý hội thoại RAG (/chat)
│   │           ├── tickets.py      # Endpoint CRUD & Lọc danh sách Ticket (/tickets)
│   │           ├── agent.py        # Endpoint AI Copilot hỗ trợ tư vấn viên (/agent)
│   │           ├── knowledge.py    # Endpoint tra cứu kho tri thức FAQ (/knowledge)
│   │           └── health.py       # Endpoint kiểm tra trạng thái & đo độ trễ (/health)
│   ├── core/
│   │   ├── config.py               # Quản lý biến môi trường (.env) và tham số hệ thống
│   │   ├── security.py             # Lọc mã độc, vệ sinh chuỗi & chống Prompt Injection
│   │   └── exceptions.py           # Định nghĩa ngoại lệ tùy biến và bộ xử lý lỗi RFC 7807
│   ├── db/
│   │   ├── base.py                 # Lớp cơ sở DeclarativeBase của SQLAlchemy
│   │   └── session.py              # Async Engine, session context & nạp dữ liệu mẫu
│   ├── models/
│   │   ├── ticket.py               # SQLAlchemy ORM Model cho bảng Ticket
│   │   └── knowledge.py            # SQLAlchemy ORM Model cho bảng FAQ & Knowledge Chunk
│   ├── schemas/
│   │   ├── chat.py                 # Pydantic Schemas cho yêu cầu/phản hồi Chat & Citations
│   │   ├── ticket.py               # Pydantic Schemas cho Ticket (Create, Update, Response)
│   │   ├── knowledge.py            # Pydantic Schemas cho bài viết tri thức
│   │   └── health.py               # Pydantic Schemas cho Health check & Smoke test
│   └── services/
│       ├── llm_service.py          # Wrapper kết nối Google Gemini 3.5 Flash Lite / Ollama (Timeout 4s)
│       ├── fallback_service.py     # Thuật toán tìm kiếm BM25 thuần Python (Zero-LLM Fallback)
│       ├── rag_service.py          # Điều phối quy trình RAG (Truy xuất context -> Gọi AI -> Fallback)
│       └── ticket_service.py       # Tính SLA, phân loại AI tags và soạn trước câu trả lời mẫu
└── tests/
    └── test_api.py                 # Bộ kiểm thử tự động toàn diện (Integration & Smoke Tests)
```

---

## 2. Chi Tiết Từng File Mã Nguồn

---

### `app/main.py` - Điểm Khởi Chạy Ứng Dụng (Application Entrypoint)
*   **Vị trí:** `backend/app/main.py`
*   **Vai trò:** Khởi tạo đối tượng `FastAPI()`, đóng vai trò là "trung tâm điều khiển" của toàn bộ backend.
*   **Các thành phần chính:**
    1.  `lifespan(app: FastAPI)`: Hàm quản lý vòng đời ứng dụng. Khi server khởi động, nó tự động gọi `init_db()` để tạo bảng và nạp dữ liệu mẫu vào CSDL.
    2.  `CORSMiddleware`: Cấu hình cho phép các ứng dụng Frontend (như Vite ở cổng `5173`) gọi API mà không bị trình duyệt chặn CORS.
    3.  `add_process_time_header`: Middleware HTTP đo thời gian xử lý của mỗi request (tính bằng mili-giây) và gắn vào header trả về `X-Process-Time-Ms`.
    4.  Đăng ký các Exception Handler toàn cục (`smartdesk_exception_handler`, `generic_exception_handler`) và gắn router tổng (`app.include_router(api_router, prefix="/api/v1")`).

---

### `app/core/` - Tầng Cốt Lõi Hệ Thống

#### 1. `app/core/config.py` - Cấu Hình Tập Trung
*   **Vị trí:** `backend/app/core/config.py`
*   **Vai trò:** Đọc và kiểm tra tính hợp lệ của các biến môi trường từ file `.env` bằng thư viện `pydantic-settings`.
*   **Các tham số tiêu biểu:**
    *   `GEMINI_API_KEY`: Khóa API Google Gemini.
    *   `LLM_MODEL_NAME`: Mặc định là `gemini-3.5-flash-lite`.
    *   `EMBEDDING_MODEL_NAME`: Mặc định là `gemini-embedding-001`.
    *   `LLM_TIMEOUT_SECONDS`: Giới hạn thời gian chờ phản hồi LLM (mặc định là `4.0` giây).
    *   `DATABASE_URL`: Đường dẫn kết nối CSDL (mặc định dùng SQLite bất đồng bộ `sqlite+aiosqlite:///./smartdesk.db`).
    *   `CORS_ORIGINS`: Danh sách các domain Frontend được cấp quyền gọi API.
    *   `resolved_seed_faq_path`: Tự động tìm chính xác đường dẫn tuyệt đối đến file `seed_faq.json`.

#### 2. `app/core/security.py` - Bảo Mật & Phòng Vệ Prompt Injection
*   **Vị trí:** `backend/app/core/security.py`
*   **Vai trò:** Bảo vệ backend và mô hình AI trước các đoạn văn bản độc hại, câu lệnh bẻ khóa (jailbreak).
*   **Các hàm chính:**
    *   `sanitize_input(text, max_length=4000)`: Loại bỏ các ký tự điều khiển ẩn (null bytes, non-printable characters) và giới hạn độ dài ký tự để tránh tràn bộ đệm.
    *   `check_prompt_injection(text)`: Quét văn bản với các biểu thức chính quy (Regex) của các mẫu tấn công phổ biến như `ignore previous instructions`, `dan mode`, `system prompt override`, `bypass all filters`. Trả về `(True, lý do)` nếu phát hiện dấu hiệu vi phạm.

#### 3. `app/core/exceptions.py` - Quản Lý Lỗi & Ngoại Lệ
*   **Vị trí:** `backend/app/core/exceptions.py`
*   **Vai trò:** Chuẩn hóa toàn bộ thông báo lỗi theo chuẩn RFC 7807 (Problem Details for HTTP APIs).
*   **Các lớp ngoại lệ chính:**
    *   `SmartDeskException`: Lớp cơ sở cho toàn bộ exception trong hệ thống.
    *   `InvalidPromptException`: Ném ra khi phát hiện Prompt Injection (HTTP 400).
    *   `TicketNotFoundException`: Ném ra khi không tìm thấy ticket theo mã hoặc ID (HTTP 404).
    *   `LLMTimeoutException`: Ném ra khi cuộc gọi Gemini vượt quá 4.0s (HTTP 504).
    *   `LLMServiceException`: Ném ra khi lỗi kết nối mạng hoặc sai API Key (HTTP 502).

---

### `app/db/` - Quản Lý Kết Nối Cơ Sở Dữ Liệu

#### 1. `app/db/base.py` - Base Model Declarative
*   **Vị trí:** `backend/app/db/base.py`
*   **Vai trò:** Khai báo lớp `Base(DeclarativeBase)` của SQLAlchemy 2.0. Tất cả các Model ORM trong dự án đều kế thừa từ lớp này để SQLAlchemy theo dõi và tạo bảng.

#### 2. `app/db/session.py` - Quản Lý Phiên Async & Seed Dữ Liệu
*   **Vị trí:** `backend/app/db/session.py`
*   **Vai trò:** Thiết lập kết nối bất đồng bộ và khởi tạo dữ liệu mẫu ban đầu.
*   **Các thành phần chính:**
    *   `normalize_database_url()`: Tự động chuyển đổi chuỗi kết nối sang driver async (`postgresql+asyncpg://` hoặc `sqlite+aiosqlite:///`).
    *   `get_db()`: FastAPI Dependency cung cấp `AsyncSession` cho từng API request, tự động commit khi thành công và rollback khi có lỗi.
    *   `init_db()`: Hàm tự động chạy lúc server bật:
        *   Đồng bộ cấu trúc bảng vào database (nếu chưa có).
        *   Tự động nạp danh sách câu hỏi FAQ từ `seed_faq.json` vào bảng `faq_items`.
        *   Tự động nạp sẵn 3 ticket mẫu (`#TICK-1042`, `#TICK-1041`, `#TICK-1039`) để phục vụ kiểm thử ngay lập tức.

---

### `app/models/` - Định Nghĩa Thực Thể CSDL (SQLAlchemy ORM)

#### 1. `app/models/ticket.py` - Model Vé Hỗ Trợ (Ticket)
*   **Vị trí:** `backend/app/models/ticket.py`
*   **Vai trò:** Định nghĩa bảng `tickets` trong database.
*   **Các trường dữ liệu quan trọng:**
    *   `ticket_code`: Mã vé định dạng chuỗi `#TICK-XXXX` (Unique, có index).
    *   `customer_name`, `customer_email`: Thông tin khách hàng.
    *   `category`, `priority`: Phân loại và mức độ khẩn cấp (`Low`, `Medium`, `High`, `Urgent`).
    *   `status`: Trạng thái xử lý (`open`, `in_progress`, `resolved`).
    *   `ai_tags`: Danh sách nhãn phân loại do AI tự trích xuất (lưu dưới dạng JSON).
    *   `ai_draft_reply`: Bản thảo phản hồi do AI chuẩn bị sẵn cho nhân viên hỗ trợ.
    *   `estimated_response_hours`: Thời hạn SLA cam kết (tính theo giờ).

#### 2. `app/models/knowledge.py` - Model Cơ Sở Tri Thức
*   **Vị trí:** `backend/app/models/knowledge.py`
*   **Vai trò:** Định nghĩa bảng `faq_items` (bài viết hỏi đáp chuẩn hóa) và `knowledge_chunks` (các đoạn văn bản chia nhỏ để phục vụ tìm kiếm vector).

---

### `app/schemas/` - Chuẩn Hóa Dữ Liệu Vào/Ra (Pydantic v2)

*   `app/schemas/chat.py`: Chứa `ChatRequest` (tin nhắn gửi lên từ khách hàng) và `ChatResponse` (câu trả lời của AI, danh sách trích dẫn `citations`, độ trễ `latency_ms`, cờ `is_fallback`, đề xuất mở ticket `escalation_recommended`).
*   `app/schemas/ticket.py`: Chứa `TicketCreate` (dữ liệu khách điền form), `TicketUpdate` (nhân viên cập nhật trạng thái/sửa bản thảo phản hồi) và `TicketResponse` (dữ liệu trả về cho frontend).
*   `app/schemas/knowledge.py`: Chứa schema hiển thị chi tiết bài viết tri thức (`KnowledgeItemResponse`).
*   `app/schemas/health.py`: Chứa cấu trúc phản hồi kiểm tra sức khỏe CSDL (`HealthResponse`) và kết quả đo độ trễ thực tế LLM (`SmokeTestResponse`).

---

### `app/services/` - Trái Tim Nghiệp Vụ (Business Logic)

#### 1. `app/services/llm_service.py` - Kết Nối Google Gemini 3.5 Flash Lite
*   **Vị trí:** `backend/app/services/llm_service.py`
*   **Vai trò:** Quản lý giao tiếp trực tiếp với Google Gemini AI.
*   **Đặc điểm nổi bật:**
    *   Hỗ trợ cả SDK mới nhất `google-genai` lẫn SDK tiền nhiệm `google-generativeai`.
    *   Áp dụng `temperature: 0.2` để câu trả lời có tính chuẩn xác cao, không bịa đặt (hallucination).
    *   Bọc cuộc gọi trong `asyncio.wait_for(..., timeout=4.0)` để ngắt dứt khoát nếu Gemini phản hồi quá 4 giây.

#### 2. `app/services/fallback_service.py` - Bộ Máy BM25 Dự Phòng Thuần Python
*   **Vị trí:** `backend/app/services/fallback_service.py`
*   **Vai trò:** Cung cấp cơ chế tìm kiếm thông minh mà **không cần LLM và không cần Internet**.
*   **Cách hoạt động:**
    *   `BM25Engine`: Cài đặt thuật toán xếp hạng thông tin Okapi BM25 chuẩn từ đầu bằng toán học thuần Python (`math.log`, TF-IDF, chiều dài tài liệu).
    *   Khi AI lỗi hoặc timeout, hàm `match_faq(query)` sẽ đối soát câu hỏi với tập dữ liệu `seed_faq.json`, tìm ra bài viết khớp nhất trong < 10ms và tạo câu trả lời dự phòng có căn cứ kèm đường dẫn trích dẫn.

#### 3. `app/services/rag_service.py` - Điều Phối Quy Trình RAG & Circuit Breaker
*   **Vị trí:** `backend/app/services/rag_service.py`
*   **Vai trò:** "Nhạc trưởng" điều phối toàn bộ quy trình Hỏi - Đáp của khách hàng.
*   **Quy trình 3 bước:**
    1.  *Retrieve (Truy xuất):* Tìm kiếm Top 3 bài viết FAQ phù hợp nhất từ Database/BM25 Index.
    2.  *Augment (Tăng cường Prompt):* Ghép các bài viết tìm được vào lời nhắc làm ngữ cảnh chứng minh duy nhất, nghiêm cấm mô hình bịa đặt ngoài phạm vi này.
    3.  *Generate & Circuit Breaker (Sinh câu trả lời & Dự phòng):* Gọi `llm_service`. Nếu thành công $\rightarrow$ Trả về câu trả lời kèm Citations. Nếu gặp lỗi/timeout $\rightarrow$ Tự động chuyển ngay sang `fallback_service` mà không làm sập API.

#### 4. `app/services/ticket_service.py` - Tự Động Hóa Xử Lý Vé & AI Copilot
*   **Vị trí:** `backend/app/services/ticket_service.py`
*   **Vai trò:** Tự động hóa các nghiệp vụ hỗ trợ khách hàng.
*   **Các tính năng chính:**
    *   `calculate_sla_hours(priority)`: Gán cam kết thời gian phản hồi: Urgent (2h), High (4h), Medium (8h), Low (24h).
    *   `extract_ai_tags()`: Phân tích nội dung tiêu đề và mô tả để tự động gán nhãn chuyên môn (VD: `2FA Recovery`, `Refund Request`, `Rate Limit 429`).
    *   `generate_draft_reply()`: Dùng AI tổng hợp câu trả lời lịch sự, đầy đủ lời chào tên khách hàng, hướng dẫn chi tiết các bước xử lý để nhân viên hỗ trợ sẵn sàng sử dụng.
    *   `create_ticket()`: Tự động đánh số thứ tự tiếp theo dạng `#TICK-104x` và lưu bản ghi vào CSDL.

---

### `app/api/v1/` - Tầng Định Tuyến & Giao Tiếp API (Endpoints)

*   `app/api/v1/api.py`: Gom toàn bộ các router con thành một router duy nhất gắn tiền tố `/api/v1`.
*   `endpoints/chat.py`: Xử lý `POST /api/v1/chat`. Tiến hành lọc Prompt Injection rồi chuyển qua `rag_service`.
*   `endpoints/tickets.py`:
    *   `POST /api/v1/tickets`: Tạo mới vé hỗ trợ.
    *   `GET /api/v1/tickets`: Lấy danh sách vé có lọc theo trạng thái (`status`), mức độ (`priority`), phân loại (`category`) hoặc tìm kiếm tự do (`search`).
    *   `GET /api/v1/tickets/{ticket_id}`: Xem chi tiết một vé bằng ID số hoặc mã `#TICK-XXXX`.
    *   `PATCH /api/v1/tickets/{ticket_id}`: Cập nhật trạng thái vé và chỉnh sửa bản thảo phản hồi.
*   `endpoints/agent.py`: `POST /api/v1/agent/tickets/{ticket_id}/generate-draft` cho phép nhân viên bấm nút yêu cầu AI Copilot sinh lại bản thảo phản hồi mới.
*   `endpoints/knowledge.py`: `GET /api/v1/knowledge` và `GET /api/v1/knowledge/{doc_id}` để duyệt và xem chi tiết các bài viết trong kho tri thức.
*   `endpoints/health.py`: `GET /api/v1/health` (kiểm tra trạng thái kết nối DB) và `GET /api/v1/health/smoke-test` (gọi thử nghiệm mô hình Gemini và đo độ trễ thực tế).

---

### `tests/test_api.py` - Bộ Kiểm Thử Tự Động Toàn Diện
*   **Vị trí:** `backend/tests/test_api.py`
*   **Vai trò:** Sử dụng `pytest` và `pytest-asyncio` với HTTP client bất đồng bộ `httpx.AsyncClient` để kiểm tra độ tin cậy của toàn bộ hệ thống mà không cần bật server thủ công.
*   **Các kịch bản kiểm thử (Test Cases):**
    1.  Kiểm tra endpoint `health` và `smoke-test`.
    2.  Kiểm tra luồng hội thoại RAG và cơ chế Circuit Breaker Fallback.
    3.  Kiểm tra hệ thống phòng ngự Prompt Injection (phải trả về mã lỗi HTTP 400).
    4.  Kiểm tra tạo ticket, tự động sinh mã `#TICK-XXXX`, tính toán SLA và tạo nháp phản hồi.
    5.  Kiểm tra lọc danh sách ticket và cập nhật trạng thái qua phương thức PATCH.
    6.  Kiểm tra endpoint tái tạo nháp trả lời của AI Copilot.

---

## 3. Bảng Tóm Tắt Tương Tác Giữa Các File

| Nhiệm Vụ | Luồng Gọi Giữa Các File |
| :--- | :--- |
| **Khách Chat RAG** | `endpoints/chat.py` $\rightarrow$ `core/security.py` $\rightarrow$ `services/rag_service.py` $\rightarrow$ `services/llm_service.py` *(hoặc `services/fallback_service.py` nếu lỗi)* |
| **Tạo Ticket Mới** | `endpoints/tickets.py` $\rightarrow$ `core/security.py` $\rightarrow$ `services/ticket_service.py` $\rightarrow$ `models/ticket.py` $\rightarrow$ `db/session.py` |
| **Tạo lại Draft AI** | `endpoints/agent.py` $\rightarrow$ `services/ticket_service.py` $\rightarrow$ `services/llm_service.py` $\rightarrow$ `models/ticket.py` |
| **Kiểm tra Sức Khỏe** | `endpoints/health.py` $\rightarrow$ `db/session.py` *(SELECT 1)* $\rightarrow$ `services/llm_service.py` |
