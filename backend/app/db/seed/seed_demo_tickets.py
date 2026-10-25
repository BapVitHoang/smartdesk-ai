"""Seed deterministic demo tickets for pagination, sorting and isolation testing (REQ-30, REQ-31)."""

import logging
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ticket import Ticket

logger = logging.getLogger("smartdesk.seed.demo_tickets")


def _get_sla_hours(priority: str) -> int:
    mapping = {"Urgent": 2, "High": 4, "Medium": 8, "Low": 24}
    return mapping.get(priority, 24)


# Base deterministic timestamp: 2026-10-01 08:00:00 UTC
_BASE_TIME = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)


def _generate_40_demo_tickets() -> List[Ticket]:
    """Generates 40 deterministic Ticket models with diverse properties."""
    tickets: List[Ticket] = []

    # Specification table for 40 tickets:
    # (ticket_code, customer_name, customer_email, category, priority, status, workspace_id, subject, description, day_offset, hour_offset)
    specs = [
        # --- 14 tickets for an.nguyen@company.vn (Customer isolation test) ---
        ("#TICK-1101", "Nguyễn Văn An", "an.nguyen@company.vn", "Billing", "High", "open", 1,
         "Yêu cầu xuất hóa đơn VAT điện tử cho kỳ thanh toán tháng 9",
         "Doanh nghiệp chúng tôi đã thanh toán gói Enterprise tháng 9 nhưng chưa nhận được hóa đơn điện tử gửi về email kế toán.", 1, 1),
        ("#TICK-1102", "Nguyễn Văn An", "an.nguyen@company.vn", "Authentication", "Urgent", "in_progress", 1,
         "Cảnh báo đăng nhập bất thường từ dải IP lạ",
         "Hệ thống gửi email thông báo có phiên đăng nhập từ IP nước ngoài lúc 3:00 sáng. Yêu cầu khóa tạm thời các token cũ.", 2, 3),
        ("#TICK-1103", "Nguyễn Văn An", "an.nguyen@company.vn", "Bug Report", "Medium", "resolved", 1,
         "Nút xuất báo cáo PDF bị tràn lề khi dùng ngôn ngữ tiếng Việt",
         "File PDF tải về bị cắt mất cột ngày tháng ở trang thứ hai khi bảng có trên 50 dòng.", 3, 5),
        ("#TICK-1104", "Nguyễn Văn An", "an.nguyen@company.vn", "Feature Request", "Low", "open", 1,
         "Hỗ trợ Webhook gửi thông báo sự cố sang kênh Telegram",
         "Chúng tôi muốn nhận thông báo khi có ticket mức độ Urgent ngay trên nhóm chat kỹ thuật Telegram.", 4, 2),
        ("#TICK-1105", "Nguyễn Văn An", "an.nguyen@company.vn", "General", "Low", "resolved", 1,
         "Hướng dẫn thủ tục chuyển đổi chủ sở hữu workspace",
         "Vui lòng hướng dẫn các bước chuyển quyền quản trị workspace cho người kế nhiệm vị trí Trưởng nhóm.", 5, 4),
        ("#TICK-1106", "Nguyễn Văn An", "an.nguyen@company.vn", "Billing", "High", "in_progress", 1,
         "Trừ tiền 2 lần khi gia hạn tự động qua thẻ Visa",
         "Giao dịch gia hạn định kỳ tháng 10 bị trừ tiền 2 lần liên tiếp cách nhau 2 giây trên sao kê ngân hàng.", 6, 6),
        ("#TICK-1107", "Nguyễn Văn An", "an.nguyen@company.vn", "Bug Report", "Urgent", "open", 1,
         "Lỗi 500 khi tải lên tài liệu định dạng DOCX dung lượng 8MB",
         "Khi tải file hướng dẫn vận hành vào Knowledge Studio, hệ thống báo lỗi máy chủ nội bộ 500.", 7, 1),
        ("#TICK-1108", "Nguyễn Văn An", "an.nguyen@company.vn", "Authentication", "Medium", "resolved", 1,
         "Không thể thay đổi email nhận thông báo bảo mật",
         "Trang cài đặt hồ sơ báo lỗi không lưu được khi cập nhật địa chỉ email thông báo bảo mật mới.", 8, 3),
        ("#TICK-1109", "Nguyễn Văn An", "an.nguyen@company.vn", "Feature Request", "Low", "in_progress", 1,
         "Tích hợp đăng nhập một lần SSO với Okta SAML 2.0",
         "Đề xuất bổ sung tích hợp Okta SAML để đồng bộ tài khoản người dùng nội bộ công ty.", 9, 5),
        ("#TICK-1110", "Nguyễn Văn An", "an.nguyen@company.vn", "General", "Medium", "open", 1,
         "Tư vấn nâng cấp gói tài khoản từ Team lên Enterprise",
         "Công ty chúng tôi sắp mở rộng thêm 2 chi nhánh, cần tư vấn chính sách giá và dung lượng lưu trữ.", 10, 2),
        ("#TICK-1111", "Nguyễn Văn An", "an.nguyen@company.vn", "Billing", "Low", "resolved", 1,
         "Thay đổi thông tin địa chỉ trên hóa đơn giá trị gia tăng",
         "Công ty vừa đổi trụ sở kinh doanh, nhờ cập nhật lại địa chỉ mới trên hóa đơn điện tử hàng tháng.", 11, 4),
        ("#TICK-1112", "Nguyễn Văn An", "an.nguyen@company.vn", "Bug Report", "High", "in_progress", 1,
         "Không thể đồng bộ danh bạ khách hàng từ CRM qua API",
         "Endpoint /api/v1/customers/sync trả về mã lỗi 422 Unprocessable Entity khi có trường số điện thoại quốc tế.", 12, 6),
        ("#TICK-1113", "Nguyễn Văn An", "an.nguyen@company.vn", "Authentication", "Urgent", "open", 1,
         "Tài khoản phụ bị vô hiệu hóa sau 3 lần nhập sai mã PIN",
         "Nhân viên phụ trách trực đêm nhập sai mã bảo vệ, đề nghị mở khóa khẩn cấp để kịp xử lý ca trực.", 13, 1),
        ("#TICK-1114", "Nguyễn Văn An", "an.nguyen@company.vn", "Feature Request", "Low", "resolved", 1,
         "Bổ sung chế độ giao diện tối Dark Mode cho Dashboard",
         "Giao diện hiện tại khá sáng khi làm việc vào ca đêm, đề xuất bổ sung giao diện nền tối.", 14, 3),

        # --- 5 tickets for admin@smartdesk.ai (Support Staff filed tickets) ---
        ("#TICK-1115", "Quản trị viên SmartDesk", "admin@smartdesk.ai", "Bug Report", "Urgent", "in_progress", 1,
         "Cảnh báo tải cao bất thường trên cụm cơ sở dữ liệu phụ",
         "Tiến trình tổng hợp số liệu báo cáo tự động lúc 00:00 gây nghẽn kết nối tạm thời trên cụm DB replica.", 15, 2),
        ("#TICK-1116", "Quản trị viên SmartDesk", "admin@smartdesk.ai", "General", "Medium", "open", 1,
         "Lịch bảo trì nâng cấp định kỳ hệ thống cơ sở hạ tầng đám mây",
         "Thông báo kế hoạch bảo trì nâng cấp cụm máy chủ khu vực Châu Á Thái Bình Dương vào cuối tuần.", 16, 4),
        ("#TICK-1117", "Quản trị viên SmartDesk", "admin@smartdesk.ai", "Authentication", "High", "resolved", 1,
         "Thu hồi khóa truy cập API cũ của đối tác tích hợp thanh toán",
         "Đã hoàn tất việc thu hồi và cấp mới API key theo chính sách xoay vòng bảo mật định kỳ 90 ngày.", 17, 1),
        ("#TICK-1118", "Quản trị viên SmartDesk", "admin@smartdesk.ai", "Billing", "Low", "open", 1,
         "Kiểm tra đối soát số dư chênh lệch với cổng trung gian",
         "Số liệu báo cáo cuối ngày có chênh lệch 1 giao dịch hủy hoàn tiền, chuyển phòng kế toán đối soát.", 18, 3),
        ("#TICK-1119", "Quản trị viên SmartDesk", "admin@smartdesk.ai", "Feature Request", "Medium", "in_progress", 1,
         "Nghiên cứu nâng cấp phiên bản mô hình nhúng pgvector HNSW",
         "Đánh giá hiệu năng tìm kiếm tương đồng vector khi chuyển từ Flat sang chỉ mục HNSW cho tập dữ liệu lớn.", 19, 5),

        # --- 21 tickets for other diverse customers (Workspaces 1, 2, 3) ---
        ("#TICK-1120", "Lê Thị Thảo", "thao.le@company.vn", "Billing", "High", "open", 1,
         "Chưa nhận được mã kích hoạt bản quyền sau khi thanh toán",
         "Tôi đã thanh toán qua thẻ tín dụng từ sáng nhưng hộp thư đến vẫn chưa có mã kích hoạt tài khoản.", 20, 1),
        ("#TICK-1121", "Lê Thị Thảo", "thao.le@company.vn", "General", "Low", "resolved", 1,
         "Hỏi về giới hạn số lượng câu hỏi RAG trong ngày",
         "Cho tôi hỏi tài khoản Pro có bị giới hạn số lần trò chuyện với bot hỗ trợ hàng ngày không?", 21, 3),
        ("#TICK-1122", "Lê Thị Thảo", "thao.le@company.vn", "Bug Report", "Medium", "in_progress", 1,
         "Thời gian phản hồi của chatbot chậm vào giờ cao điểm",
         "Trong khoảng 14:00 - 15:00 chatbot trả lời mất khoảng 5 giây mới hiện phản hồi đầu tiên.", 22, 5),
        ("#TICK-1123", "Lê Thị Thảo", "thao.le@company.vn", "Authentication", "Urgent", "open", 1,
         "Không đăng nhập được bằng nút Google Single Sign-On",
         "Khi bấm nút đăng nhập bằng Google thì màn hình bị trắng tinh và không chuyển hướng về trang chủ.", 23, 2),

        ("#TICK-1124", "Phạm Minh Tuấn", "tuan.pham@corp.io", "Feature Request", "Low", "open", 1,
         "Hỗ trợ phân quyền xem ticket theo từng phòng ban nội bộ",
         "Đề xuất cho phép trưởng phòng chỉ xem các ticket thuộc phòng ban mình thay vì thấy toàn bộ công ty.", 24, 4),
        ("#TICK-1125", "Phạm Minh Tuấn", "tuan.pham@corp.io", "Billing", "Medium", "resolved", 1,
         "Chuyển đổi hình thức thanh toán từ thẻ cá nhân sang thẻ doanh nghiệp",
         "Đã cập nhật thông tin thẻ thanh toán mới của công ty, nhờ hệ thống kích hoạt tự động trừ phí.", 25, 1),
        ("#TICK-1126", "Phạm Minh Tuấn", "tuan.pham@corp.io", "Bug Report", "High", "in_progress", 1,
         "Lỗi hiển thị ký tự tiếng Việt có dấu trong trích dẫn tài liệu",
         "Phần trích dẫn citation bên dưới câu trả lời bị lỗi font hiển thị ô vuông với các từ có dấu ngã.", 26, 3),
        ("#TICK-1127", "Phạm Minh Tuấn", "tuan.pham@corp.io", "General", "Low", "open", 1,
         "Tài liệu hướng dẫn tích hợp SDK trên nền tảng di động",
         "Công ty đang muốn nhúng widget SmartDesk vào app React Native, xin tài liệu hướng dẫn chi tiết.", 27, 5),

        ("#TICK-1128", "Đỗ Quốc Bảo", "bao.do@service.vn", "Authentication", "Medium", "open", 2,
         "Đặt lại mật khẩu cho bác sĩ trực phòng khám SmileCare",
         "Bác sĩ phụ trách cơ sở 2 quên mật khẩu đăng nhập hệ thống quản lý lịch hẹn khám răng.", 28, 2),
        ("#TICK-1129", "Đỗ Quốc Bảo", "bao.do@service.vn", "General", "Low", "resolved", 2,
         "Cập nhật bảng giá niềng răng trong suốt Invisalign năm 2026",
         "Phòng khám vừa cập nhật chính sách ưu đãi niềng răng mới, nhờ tải lại tài liệu vào workspace SmileCare.", 29, 4),
        ("#TICK-1130", "Đỗ Quốc Bảo", "bao.do@service.vn", "Bug Report", "High", "in_progress", 2,
         "Bot trả lời sai thông tin bảo hành dịch vụ tẩy trắng răng",
         "Khách hỏi bảo hành tẩy trắng bot báo 5 năm, trong khi chính sách thực tế chỉ là 6 tháng.", 30, 1),
        ("#TICK-1131", "Đỗ Quốc Bảo", "bao.do@service.vn", "Billing", "Urgent", "open", 2,
         "Lỗi thanh toán cọc giữ chỗ điều trị Implant qua máy POS",
         "Giao dịch quẹt thẻ báo thành công tại quầy nhưng dữ liệu chưa nhảy về lịch sử thanh toán trên web.", 31, 3),

        ("#TICK-1132", "Ngô Thùy Trang", "trang.ngo@fictional.vn", "General", "Low", "open", 3,
         "Hỏi về chính sách đổi trả máy giặt trong vòng 30 ngày",
         "Tôi mới mua máy giặt tại TechStore 5 ngày trước, nếu muốn nâng cấp lên dòng sấy thì phụ phí thế nào?", 32, 2),
        ("#TICK-1133", "Ngô Thùy Trang", "trang.ngo@fictional.vn", "Bug Report", "Medium", "resolved", 3,
         "Không xem được video mở hộp sản phẩm trên trang chi tiết",
         "Đường link nhúng YouTube bị lỗi không phát được trên trình duyệt điện thoại Safari.", 33, 4),
        ("#TICK-1134", "Ngô Thùy Trang", "trang.ngo@fictional.vn", "Billing", "High", "in_progress", 3,
         "Hóa đơn điện tử ghi sai số thuế công ty người mua",
         "Số thuế công ty bị nhập thiếu 1 chữ số ở cuối, đề nghị kế toán TechStore hủy và xuất lại hóa đơn điều chỉnh.", 34, 1),

        ("#TICK-1135", "Vũ Đình Hùng", "hung.vu@techhub.vn", "Authentication", "Urgent", "open", 1,
         "Mất điện thoại chứa ứng dụng Google Authenticator",
         "Tôi bị rơi điện thoại không thể lấy mã xác thực 2 bước, nhờ hỗ trợ xác minh giấy tờ để reset 2FA.", 35, 3),
        ("#TICK-1136", "Vũ Đình Hùng", "hung.vu@techhub.vn", "Bug Report", "High", "in_progress", 1,
         "API báo rate limit 429 dù mới gửi 10 requests trong phút",
         "Hệ thống báo vượt ngưỡng tần suất quá sớm so với hạn mức cam kết trong gói trả phí doanh nghiệp.", 36, 5),
        ("#TICK-1137", "Vũ Đình Hùng", "hung.vu@techhub.vn", "Feature Request", "Low", "resolved", 1,
         "Cho phép tùy biến thông điệp chào mừng theo từng kênh mạng xã hội",
         "Mong muốn có câu chào mở đầu riêng biệt khi khách hàng nhắn tin từ Zalo OA và Facebook Messenger.", 37, 2),

        ("#TICK-1138", "Đặng Mỹ Linh", "linh.dang@enterprise.com", "Billing", "Medium", "open", 1,
         "Yêu cầu báo giá hợp đồng hỗ trợ kỹ thuật 24/7 theo năm",
         "Đơn vị chúng tôi chuẩn bị ngân sách CNTT cho năm tới, cần bảng báo giá chính thức kèm cam kết SLA 2 giờ.", 38, 4),
        ("#TICK-1139", "Đặng Mỹ Linh", "linh.dang@enterprise.com", "General", "Low", "resolved", 1,
         "Chứng nhận tuân thủ bảo mật tiêu chuẩn ISO 27001 của SmartDesk",
         "Phòng an ninh thông tin yêu cầu cung cấp tài liệu chứng nhận bảo mật dữ liệu trước khi ký hợp đồng chính thức.", 39, 1),
        ("#TICK-1140", "Đặng Mỹ Linh", "linh.dang@enterprise.com", "Bug Report", "Urgent", "in_progress", 1,
         "Mất kết nối cơ sở dữ liệu ngắt quãng vào lúc 12:00 trưa",
         "Toàn bộ nhân viên chăm sóc khách hàng bị gián đoạn truy cập khoảng 3 phút trong ca trực trưa nay.", 40, 3),
    ]

    for (code, name, email, cat, prio, stat, ws_id, subj, desc, day_off, hr_off) in specs:
        created = _BASE_TIME + timedelta(days=day_off, hours=hr_off)
        sla_hrs = _get_sla_hours(prio)
        t = Ticket(
            workspace_id=ws_id,
            ticket_code=code,
            customer_name=name,
            customer_email=email,
            category=cat,
            priority=prio,
            subject=subj,
            description=desc,
            status=stat,
            ai_tags=[cat, prio, f"Workspace {ws_id}"],
            ai_draft_reply=f"Chào bạn, SmartDesk AI đã tiếp nhận yêu cầu về '{subj}'. Bộ phận hỗ trợ sẽ xử lý theo thời hạn SLA cam kết ({sla_hrs} giờ).",
            estimated_response_hours=sla_hrs,
            created_at=created,
            updated_at=created,
        )
        tickets.append(t)

    return tickets


async def seed_demo_tickets(session: AsyncSession) -> None:
    """Seeds 40 deterministic demo tickets if DEMO_LOGIN_ENABLED is True and ticket count <= 3."""
    if not settings.DEMO_LOGIN_ENABLED:
        logger.info("DEMO_LOGIN_ENABLED is False; skipping 40 demo tickets seeding.")
        return

    count_res = await session.execute(select(func.count(Ticket.id)))
    current_count = count_res.scalar() or 0

    if current_count > 3:
        logger.info(f"Tickets table already has {current_count} tickets (> 3); skipping demo tickets seeding.")
        return

    logger.info("Seeding 40 deterministic demo tickets for pagination and sorting verification...")
    demo_tickets = _generate_40_demo_tickets()
    for t in demo_tickets:
        session.add(t)

    await session.commit()
    logger.info(f"Successfully seeded {len(demo_tickets)} demo tickets (Total in DB: {current_count + len(demo_tickets)}).")

