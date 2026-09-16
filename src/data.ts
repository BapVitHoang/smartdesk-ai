import { Ticket, ChatMessage } from './types';

export const INITIAL_TICKETS: Ticket[] = [
  {
    id: "TICK-1042",
    customer: "Nguyễn Văn An",
    email: "an.nguyen@company.vn",
    subject: "Lỗi thanh toán cổng VNPAY đơn hàng #9842",
    category: "Billing",
    priority: "High",
    status: "Open",
    aiTag: "Billing / High",
    date: "10:24 AM - Hôm nay",
    slaTime: "4 giờ làm việc (Cam kết SLA P2)",
    summary: "Khách bị trừ tiền tài khoản nhưng hệ thống báo đơn hàng thất bại. Đã có mã giao dịch ngân hàng kèm theo.",
    draftReply: "Chào anh An, SmartDesk AI đã xác thực mã giao dịch của anh trên cổng VNPAY. Hệ thống đã đối soát thành công và tiến hành kích hoạt đơn hàng #9842 ngay cho anh trong vòng 5 phút tới.",
    message: "Tôi đã quét mã QR thanh toán thành công lúc 10:15, tài khoản trừ 1.500.000đ nhưng trang giỏ hàng báo Timeout. Mong hỗ trợ kiểm tra gấp."
  },
  {
    id: "TICK-1041",
    customer: "Trần Mai Anh",
    email: "maianh.tran@tech.io",
    subject: "Không thể nhận email OTP đặt lại mật khẩu 2FA",
    category: "Authentication",
    priority: "Urgent",
    status: "Pending",
    aiTag: "Auth / Urgent",
    date: "09:45 AM - Hôm nay",
    slaTime: "2 giờ làm việc (Cam kết SLA P1)",
    summary: "Khách bị lock tài khoản quản trị do không nhận được mã 2FA xác thực qua email công ty.",
    draftReply: "Chào chị Mai Anh, bộ phận kỹ thuật đã kiểm tra mail server của domain @tech.io bị chặn filter tạm thời. SmartDesk đã kích hoạt phương thức phục hồi phụ qua SMS xác thực tới số điện thoại đuôi **789.",
    message: "Tôi cần truy cập tài khoản admin để duyệt hợp đồng gấp nhưng bấm gửi lại OTP 5 lần đều không nhận được mail."
  },
  {
    id: "TICK-1039",
    customer: "Lê Hoàng Quân",
    email: "quan.le@startup.co",
    subject: "Đề xuất tính năng Export báo cáo CSV tùy biến",
    category: "Feature Request",
    priority: "Low",
    status: "Resolved",
    aiTag: "Product / Low",
    date: "Hôm qua lúc 16:30",
    slaTime: "24 giờ làm việc (Cam kết SLA P4)",
    summary: "Đề xuất cho phép xuất dữ liệu thống kê agent theo khoảng ngày tùy biến ra định dạng Excel/CSV.",
    draftReply: "Cảm ơn đóng góp của anh Quân. Tính năng tùy biến Export báo cáo đã được đưa vào Roadmap phiên bản Sprint Q3.",
    message: "Hiện tại hệ thống chỉ cho tải PDF tổng hợp tháng, mong muốn có thêm nút Export CSV theo tuần."
  }
];

export const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  {
    id: "msg-1",
    sender: "bot",
    text: "Xin chào! Tôi là Trợ lý AI SmartDesk. Tôi có thể tra cứu tài liệu tri thức, giải đáp câu hỏi và hỗ trợ tạo ticket nếu cần. Bạn cần hỗ trợ gì hôm nay?",
    time: "10:00"
  },
  {
    id: "msg-2",
    sender: "user",
    text: "Làm sao để khôi phục tài khoản khi mất điện thoại cài ứng dụng Authenticator 2FA?",
    time: "10:01"
  },
  {
    id: "msg-3",
    sender: "bot",
    text: "Để khôi phục tài khoản khi mất thiết bị Authenticator, bạn thực hiện theo quy trình chuẩn sau:",
    bulletPoints: [
      "Sử dụng 1 trong 10 'Backup Recovery Codes' (Mã khôi phục khẩn cấp) được cấp khi kích hoạt 2FA.",
      "Truy cập cổng Xác minh Danh tính Dự phòng tại id.smartdesk.ai/recovery.",
      "Nếu đã làm mất cả mã Backup Codes, cần tiến hành gửi Phiếu Hỗ trợ (Ticket) đính kèm bản chụp CCCD/CMND để chuyên viên bảo mật duyệt thủ công trong 2-4h."
    ],
    citations: [
      { code: "Doc #4: Account Recovery & 2FA Bypass Protocol", link: "#" },
      { code: "KB-89: Security Verification Standards 2025", link: "#" }
    ],
    time: "10:01",
    feedbackGiven: null
  }
];

export function getRagResponse(question: string): {
  text: string;
  bulletPoints: string[];
  citations: { code: string; link: string }[];
} {
  const q = question.toLowerCase();

  if (q.includes("hoàn tiền") || q.includes("thanh toán") || q.includes("billing") || q.includes("tiền")) {
    return {
      text: `Dưới đây là thông tin tra cứu tự động về quy định hoàn tiền và xử lý lỗi thanh toán giao dịch:`,
      bulletPoints: [
        "Các giao dịch phát sinh lỗi Timeout trên cổng thanh toán (VNPAY/Momo/Stripe) được hệ thống tự động đối soát trong vòng 15-30 phút.",
        "Tiền sẽ được hoàn trả tự động vào tài khoản gốc từ 1 đến 3 ngày làm việc tùy thuộc vào ngân hàng phát hành.",
        "Nếu sau 2 giờ chưa nhận được hoàn tiền hoặc cập nhật gói, vui lòng tạo phiếu hỗ trợ đính kèm mã sao kê giao dịch."
      ],
      citations: [
        { code: "KB-301: Billing Refund Policy & Reversal SLA", link: "#" },
        { code: "Doc #18: Payment Gateway Timeout Reconciliation", link: "#" }
      ]
    };
  }

  if (q.includes("api") || q.includes("key") || q.includes("webhook") || q.includes("token")) {
    return {
      text: `Hướng dẫn khởi tạo và quản lý API Secret Key trong hệ thống SmartDesk:`,
      bulletPoints: [
        "Truy cập Cài đặt Không gian làm việc (Workspace Settings) > Nhà phát triển (Developer API).",
        "Nhấn nút 'Generate New Key', chọn phạm vi quyền (Scopes: Read/Write Tickets & RAG Query).",
        "Lưu trữ khóa bảo mật ở nơi an toàn vì khóa chỉ hiển thị 01 lần duy nhất sau khi khởi tạo."
      ],
      citations: [
        { code: "Doc #72: SmartDesk Public API Integration Guide", link: "#" },
        { code: "KB-112: Rate Limiting & Webhook Subscriptions", link: "#" }
      ]
    };
  }

  if (q.includes("sla") || q.includes("thời gian") || q.includes("cam kết")) {
    return {
      text: `Cam kết thời gian phản hồi dịch vụ (Service Level Agreement - SLA) của SmartDesk AI:`,
      bulletPoints: [
        "Mức Khẩn cấp (Urgent - P1): Phản hồi và xử lý trong vòng 2 giờ làm việc.",
        "Mức Cao (High - P2): Thời gian cam kết xử lý tối đa 4 giờ làm việc.",
        "Mức Trung bình (Medium - P3): Thời gian xử lý tiêu chuẩn trong vòng 8 giờ làm việc.",
        "Mức Thấp (Low - P4): Thời gian xử lý trong vòng 24 giờ làm việc."
      ],
      citations: [
        { code: "KB-204: Customer SLA & Escalation Guidelines", link: "#" },
        { code: "Doc #12: Enterprise Support Standards ITIL v4", link: "#" }
      ]
    };
  }

  return {
    text: `Tôi đã tra cứu cơ sở dữ liệu tri thức nội bộ cho câu hỏi: "${question}". Dưới đây là giải đáp trích xuất từ tài liệu chính thức:`,
    bulletPoints: [
      "Hệ thống SmartDesk tự động cập nhật chính sách hỗ trợ khách hàng theo chuẩn ITIL v4 mới nhất.",
      "Để điều chỉnh cài đặt tài khoản hoặc quyền truy cập, bạn có thể thực hiện tại mục Hồ sơ người dùng.",
      "Nếu câu trả lời chưa giải quyết trọn vẹn sự cố, bạn hãy nhấn nút chuyển sang Gửi Ticket phía trên để chuyển giao cho chuyên viên kỹ thuật."
    ],
    citations: [
      { code: "Doc #12: SmartDesk Knowledge Base Policy", link: "#" },
      { code: "KB-204: Customer SLA & Escalation Guidelines", link: "#" }
    ]
  };
}
