import { BackendChatResponse } from '../../types';

export const MOCK_CHAT_RESPONSES: Record<string, BackendChatResponse> = {
  default: {
    response: 'Xin chào! SmartDesk AI có thể hỗ trợ gì cho bạn hôm nay? Chúng tôi hỗ trợ giải đáp chính sách, bảo hành và xử lý sự cố kỹ thuật.',
    citations: [
      {
        doc_id: 'faq-01',
        title: 'Chính sách hoàn tiền và hủy gói',
        source_url: 'https://smartdesk.ai/docs/refund-policy',
        page: 1,
        snippet: 'Khách hàng có quyền yêu cầu hoàn tiền trong vòng 30 ngày kể từ ngày kích hoạt dịch vụ.',
      },
    ],
    latency_ms: 320,
    confidence: 0.98,
    is_fallback: false,
  },
  resetPassword: {
    response: 'Để đặt lại mật khẩu của bạn:\n1. Truy cập trang Đăng nhập\n2. Nhấn vào "Quên mật khẩu"\n3. Nhập email đã đăng ký và làm theo hướng dẫn trong thư xác nhận.',
    citations: [
      {
        doc_id: 'faq-02',
        title: 'Hướng dẫn khôi phục tài khoản và 2FA',
        source_url: 'https://smartdesk.ai/docs/account-recovery',
        page: 2,
        snippet: 'Liên kết đặt lại mật khẩu có hiệu lực trong 15 phút vì lý do bảo mật.',
      },
    ],
    latency_ms: 410,
    confidence: 0.95,
    is_fallback: false,
  },
};
