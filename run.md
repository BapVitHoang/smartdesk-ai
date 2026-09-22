# Hướng Dẫn Chạy & Kiểm Thử Dự Án SmartDesk AI

## 🚀 1. Chạy Dự Án

### Cách nhanh nhất (1 click):
Chạy file script khởi động toàn bộ hệ thống:
```cmd
.\start_all.bat
```

Hoặc chạy từng thành phần thủ công qua 2 terminal riêng biệt:

- **Terminal 1 - Chạy Backend (FastAPI):**
  ```bash
  cd backend
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

- **Terminal 2 - Chạy Frontend (React 19 + Vite):**
  ```bash
  npm start
  ```
  *(Truy cập giao diện tại: http://localhost:3000, API Swagger tại: http://localhost:8000/docs)*

---

## 🧪 2. Luồng Kiểm Thử Tự Động (Automated Testing)

### Cách 1: Chạy toàn bộ test tự động (Frontend + Backend)
Chạy script kiểm thử tổng hợp:
```cmd
.\test_all.bat
```

### Cách 2: Chạy kiểm thử từng phần

1. **Kiểm thử Frontend (TypeScript Type Check & Production Build):**
   ```bash
   npm test
   ```

2. **Kiểm thử Backend (Pytest Suite 9/9 kịch bản API & RAG):**
   ```bash
   cd backend
   python -m pytest tests/ -v
   ```

3. **Smoke Test & Đo Latency thực tế (khi Backend đang chạy):**
   ```bash
   curl http://localhost:8000/api/v1/health/smoke-test
   ```

---

## 📋 3. Ma Trận 4 Kịch Bản Kiểm Thử Chấp Nhận (Acceptance Scenarios)

| Kịch Bản | Mục Tiêu Kiểm Thử | Các Bước Thực Hiện | Kết Quả Mong Đợi |
| :--- | :--- | :--- | :--- |
| **Kịch Bản 1: Customer RAG & Trích dẫn** | Hỏi đáp hỗ trợ khách hàng với trích dẫn tài liệu | Vào tab **Chat AI Khách Hàng**, bấm gợi ý *"Đổi mật khẩu"* hoặc nhập câu hỏi | Trả lời đầy đủ các bước trong < 2s kèm Huy hiệu trích dẫn `[doc-01]` |
| **Kịch Bản 2: Fallback & Circuit Breaker** | Hệ thống tự động chuyển sang BM25 khi AI mất kết nối | Gạt bộ điều khiển demo sang chế độ **Error / Fallback** và gửi câu hỏi | Trả lời chính xác từ file FAQ dự phòng, hiển thị banner cảnh báo và nút tạo ticket khẩn |
| **Kịch Bản 3: Gửi Ticket & SLA Tự Động** | Kiểm tra validation form và sinh mã ticket | Vào tab **Gửi Yêu Cầu Hỗ Trợ**, điền thông tin (ví dụ: mất 2FA) và gửi | Hiển thị mã `#TICK-XXXX`, tính SLA phản hồi (2h cho Urgent), có nút chuyển đến Hàng chờ |
| **Kịch Bản 4: Agent Triage & AI Copilot Draft** | Điều phối ticket, phân loại tag AI và duyệt dự thảo phản hồi | Vào tab **Hàng Chờ Agent**, chọn ticket vừa tạo, xem AI gợi ý trả lời, chỉnh sửa và bấm duyệt | Cập nhật trạng thái sang `Đã xử lý` / `Đang xử lý`, hiển thị thông báo thành công |
