# Trình bày 3 AI Capabilities: A + C + E

## Chuẩn bị

- Mở frontend, backend và đăng nhập tài khoản quản trị để dùng trang 3 và 4.
- Cấu hình Gemini hoặc Ollama hoạt động; chuẩn bị một tài liệu có nội dung dễ đối chiếu.
- Kiểm tra Telemetry và log backend: kết quả dự phòng không phải minh chứng AI thật. Embedding giả cũng không chứng minh được semantic vector search.
- Thứ tự trình bày: A (hỏi đáp) → C (ticket) → E (sát hạch tri thức).

## A. RAG trên dữ liệu ứng dụng

**Định nghĩa:** RAG (Retrieval-Augmented Generation) là sinh câu trả lời có bổ sung thông tin truy xuất. Hệ thống tìm các đoạn dữ liệu liên quan đến câu hỏi, đưa chúng vào ngữ cảnh rồi yêu cầu mô hình ngôn ngữ (LLM) trả lời dựa trên đó. Đây không phải huấn luyện lại mô hình; dữ liệu được cung cấp ngay lúc xử lý câu hỏi.

**Ý chính:** Tìm nội dung liên quan trong tài liệu của workspace, đưa vào ngữ cảnh cho LLM và trả lời kèm nguồn.

**Show trên giao diện:**
1. Trang 4, **Quản lý tri thức và sát hạch AI**: chọn workspace, dùng tài liệu đã xuất bản. Nếu là tài liệu mới, tải lên, chạy sát hạch và phê duyệt trước.
2. Trang **1. Hỏi trợ lý AI**: chọn cùng workspace, hỏi một câu có đáp án rõ trong tài liệu.
3. Chỉ ra câu trả lời và mở citation để đối chiếu đoạn trích, tên nguồn và trang nếu có.
4. Hỏi thêm một chi tiết không có trong tài liệu; quan sát cách hệ thống thông báo thiếu thông tin hoặc đề nghị hỗ trợ, không tự khẳng định một đáp án.

**Chỉ code trong repo:**
- [document_service.py](../../backend/app/services/document_service.py): `recursive_character_splitter`, `process_and_store_document` xử lý tài liệu, chia đoạn và lưu dữ liệu.
- [embedding_service.py](../../backend/app/services/embedding_service.py): `get_text_embedding`, `search_similar_chunks` tạo embedding và tìm đoạn tương đồng.
- [rag_service.py](../../backend/app/services/rag_service.py): `retrieve_context_documents`, `answer_query` truy xuất, tạo câu trả lời và citations.
- [ChatView.tsx](../../frontend/src/components/ChatView.tsx): giao diện hội thoại và nguồn trích dẫn.

**Câu thuyết trình:** “Câu trả lời được tạo từ ngữ cảnh truy xuất trong dữ liệu của doanh nghiệp; người dùng có thể mở nguồn để kiểm tra.”

## C. Structured Output

**Định nghĩa:** Structured Output là đầu ra có cấu trúc: yêu cầu AI trả dữ liệu theo khuôn mẫu (schema) quy định trước, chẳng hạn JSON có các trường, kiểu dữ liệu và giá trị cho phép. Chương trình kiểm tra rồi sử dụng từng trường thay vì phải tự đoán ý từ văn bản tự do. Đúng schema không đồng nghĩa nội dung luôn đúng thực tế.

**Ý chính:** Không chỉ nhận văn bản tự do; backend yêu cầu JSON theo schema, kiểm tra bằng Pydantic rồi sử dụng kết quả trong ứng dụng.

**Show trên giao diện:**
1. Trang **2. Gửi yêu cầu hỗ trợ**: điền thông tin hợp lệ, mô tả một sự cố cụ thể rồi gửi.
2. Trang **3. Điều phối yêu cầu**: chọn đúng ticket vừa tạo, chỉ ra nhãn và **Bản nháp phản hồi do AI gợi ý**.
3. Mở code schema và bước validation bên dưới để chứng minh kết quả không chỉ là đoạn chat trông giống JSON.
4. Có thể mở DevTools → Network → request tạo ticket để đối chiếu dữ liệu trả về với nhãn và bản nháp trên UI.

**Chỉ code trong repo:**
- [ai_structured.py](../../backend/app/schemas/ai_structured.py): `TicketCopilotStructuredOutput` quy định các trường, enum và giới hạn độ dài.
- [llm_service.py](../../backend/app/services/llm_service.py): `generate_structured_output` tạo JSON theo schema và gọi `model_validate_json` để kiểm tra.
- [ticket_copilot_service.py](../../backend/app/services/ticket_copilot_service.py): `generate_ticket_triage_and_draft` gọi LLM với schema trên.
- [ticket_service.py](../../backend/app/services/ticket_service.py): `create_ticket` lấy `ai_tags`, `ai_draft_reply` từ kết quả và lưu vào ticket.

**Câu thuyết trình:** “JSON từ AI được kiểm tra cấu trúc trước khi ứng dụng dùng nhãn và bản nháp để hỗ trợ nhân viên xử lý ticket.”

**Nói đúng phạm vi:** Category và priority của ticket hiện vẫn lấy từ biểu mẫu; không trình bày rằng mọi trường AI trả về đều tự động ghi đè dữ liệu người dùng hoặc quyết định SLA.

## E. Multi-agent Workflow

**Định nghĩa:** Multi-agent Workflow là quy trình phối hợp nhiều tác tử AI, mỗi tác tử có vai trò, nhiệm vụ và đầu vào/đầu ra riêng. Kết quả được bàn giao giữa các tác tử để hoàn thành một công việc chung. Các tác tử có thể dùng cùng một mô hình với chỉ dẫn khác nhau; không bắt buộc là nhiều mô hình hoặc nhiều tiến trình độc lập.

**Ý chính:** Các vai trò khác nhau nhận đầu ra của bước trước, thực hiện nhiệm vụ riêng và lưu nhật ký bàn giao.

**Show trên giao diện:**
1. Trang 4, **Quản lý tri thức và sát hạch AI**: tải một tài liệu mới, bấm **Sát hạch AI**.
2. Mở báo cáo; chỉ ra câu hỏi, đáp án tham chiếu, câu trả lời RAG, điểm và lý do chấm.
3. Trong **Nhật ký sát hạch của 3 tác tử AI**, giải thích luồng:
   `SyntheticQAExamAgent` tạo câu hỏi → `SandboxRAGAgent` trả lời → `FaithfulnessJudgeAgent` chấm độ bám sát.
4. Chỉ log backend có `[AgentHandOff]`; mở lại báo cáo để đối chiếu trace đã lưu. Không bịa điểm hoặc thời gian chạy trước khi có kết quả.

**Chỉ code trong repo:**
- [verification_service.py](../../backend/app/services/verification_service.py): `verify_document` điều phối; `generate_synthetic_qa`, `answer_sandbox_query`, `evaluate_faithfulness` thực hiện từng vai trò.
- [verification.py](../../backend/app/models/verification.py): `VerificationReport.agent_trace_json` lưu nhật ký trong database.
- [VerificationTrace.tsx](../../frontend/src/features/knowledge/VerificationTrace.tsx): hiển thị trace từ báo cáo.
- [KnowledgeManagerView.tsx](../../frontend/src/components/KnowledgeManagerView.tsx): giao diện sát hạch, xem báo cáo và phê duyệt tài liệu.

**Câu thuyết trình:** “Đây là workflow nhiều agent theo vai trò, có đầu vào, đầu ra và bàn giao rõ ràng; nhật ký được lưu để kiểm tra lại.”

**Nói đúng phạm vi:** Đây là pipeline điều phối theo các bước cố định, không phải các agent tự chủ tự lập kế hoạch. Khi LLM lỗi, các bước có thể dùng luật dự phòng; trace xuất hiện không tự chứng minh mọi bước đã gọi AI thật.

## Chốt khi trình bày

“Nhóm chọn A, C và E: RAG trả lời từ dữ liệu có nguồn; structured output đưa JSON đã kiểm tra vào nghiệp vụ; multi-agent workflow sát hạch tri thức với nhật ký bàn giao.”

Code và test offline chứng minh luồng xử lý, không thay thế demo provider thật. Không cần dùng B hoặc D làm minh chứng chính trong kịch bản này.