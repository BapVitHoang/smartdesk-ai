import { Ticket, ChatMessage, KnowledgeArticle, Citation, Workspace, DocumentItem, DocumentChunk, VerificationReport } from './types';

export const INITIAL_FAQ_ARTICLES: KnowledgeArticle[] = [
  {
    doc_id: "faq-01",
    category: "Authentication",
    title: "How to Reset Your CloudDesk / SmartDesk Password",
    content: "To reset your password: 1. Go to the login screen and click 'Forgot Password?'. 2. Enter your registered email address. 3. Check your inbox for a secure one-time password (OTP) or reset link valid for 15 minutes. 4. If you have lost access to your primary email, choose 'Recover with backup phone number' or use your 24-character security recovery key provided during account setup. If you do not have a recovery key, contact your enterprise organization workspace administrator.",
    source_url: "/faq/auth/password-reset"
  },
  {
    doc_id: "faq-02",
    category: "Authentication",
    title: "Two-Factor Authentication (2FA) Setup and Recovery",
    content: "SmartDesk AI requires 2FA for all organization accounts. You can configure Google Authenticator, Authy, or hardware security keys (FIDO2/WebAuthn) under Settings > Security > Two-Factor Authentication. If you lose your 2FA device, enter one of your 10 single-use emergency recovery codes. If all recovery codes are exhausted, your organization workspace admin must manually reset your MFA profile via the Enterprise Console.",
    source_url: "/faq/auth/2fa-recovery"
  },
  {
    doc_id: "faq-03",
    category: "Authentication",
    title: "Single Sign-On (SSO) and SAML 2.0 Integration",
    content: "Enterprise workspaces support SSO via Okta, Microsoft Entra ID (Azure AD), Google Workspace, and generic SAML 2.0 / OIDC identity providers. To configure SSO, navigate to Admin Console > Security > Single Sign-On, download our SP Metadata XML, and paste your IdP Entity ID, SSO URL, and X.509 Certificate. Enforce SSO for all domain members under the SSO Policy toggle.",
    source_url: "/faq/auth/sso-saml"
  },
  {
    doc_id: "faq-04",
    category: "Billing",
    title: "Subscription Plans, Billing Cycles, and Upgrades",
    content: "SmartDesk AI provides three tiers: Starter ($29/seat/month), Professional ($79/seat/month), and Enterprise (Custom SLA & dedicated VPC). You can toggle between monthly and annual billing (with a 20% annual discount) under Settings > Billing > Plan Management. Upgrades take effect immediately with prorated billing for the remainder of the current billing cycle.",
    source_url: "/faq/billing/plans-and-cycles"
  },
  {
    doc_id: "faq-05",
    category: "Billing",
    title: "Payment Methods, Invoices, and Tax Receipts",
    content: "We accept major credit cards (Visa, MasterCard, American Express), PayPal, and ACH direct debit/wire transfers for Enterprise contracts over $5,000/year. Automated invoices with VAT/Tax ID numbers are sent to your designated billing email on the first day of each billing cycle and can be downloaded as PDF receipts under Settings > Billing > Invoice History.",
    source_url: "/faq/billing/invoices-tax"
  },
  {
    doc_id: "faq-06",
    category: "Billing",
    title: "Refund Policy and Cancellation Terms",
    content: "You can cancel your subscription at any time under Settings > Billing > Cancel Subscription. Your access will remain active until the end of the current billing period. We offer a full 14-day money-back guarantee for first-time paid subscriptions if you are not completely satisfied. Pro-rated refunds are evaluated on a case-by-case basis by our billing specialists upon submitting a ticket.",
    source_url: "/faq/billing/refund-policy"
  },
  {
    doc_id: "faq-07",
    category: "Technical Bug",
    title: "API Rate Limits, HTTP 429 Errors, and Exponential Backoff",
    content: "Standard API rate limits are 120 requests per minute for Starter, 600 req/min for Professional, and 3,000 req/min for Enterprise. When you exceed these limits, the server responds with HTTP 429 'Too Many Requests' and a 'Retry-After' header indicating the seconds to wait. We recommend implementing exponential backoff with jitter in your API client libraries.",
    source_url: "/faq/tech/rate-limits-429"
  },
  {
    doc_id: "faq-08",
    category: "Technical Bug",
    title: "Webhook Delivery Failures and Retry Policy",
    content: "Webhooks dispatched by SmartDesk AI timeout after 5,000ms. If your webhook endpoint returns a non-2xx status code or times out, our system retries delivery using an exponential backoff schedule: immediately, after 1 minute, 5 minutes, 30 minutes, 2 hours, and 24 hours. After 6 consecutive failed attempts, the webhook endpoint is automatically disabled and an alert notification is sent.",
    source_url: "/faq/tech/webhook-retries"
  },
  {
    doc_id: "faq-09",
    category: "Technical Bug",
    title: "Browser Compatibility, Caching, and WebSocket Disconnections",
    content: "SmartDesk AI web client requires Chrome 100+, Firefox 100+, Safari 15+, or Edge 100+. If you experience intermittent WebSocket disconnections in the Agent Dashboard or live chat, ensure your corporate proxy or VPN permits persistent WSS connections on port 443. Clearing browser cache and local storage often resolves stale UI state issues.",
    source_url: "/faq/tech/browser-websocket"
  },
  {
    doc_id: "faq-10",
    category: "Feature Request",
    title: "Knowledge Base Document Sync: Notion, Confluence, and Zendesk",
    content: "SmartDesk AI supports automated vector ingestion from Notion workspaces, Atlassian Confluence spaces, and Zendesk Help Centers. Go to Settings > Knowledge Synthesizer > Integrations, authorize your provider with OAuth2, and select which collections or spaces to index. Document updates are synchronized every 6 hours by default, or instantly via manual webhook triggers.",
    source_url: "/faq/features/kb-sync"
  },
  {
    doc_id: "faq-11",
    category: "Feature Request",
    title: "Custom LLM Fine-Tuning and Private Model Deployment",
    content: "Enterprise customers can bring their own custom fine-tuned weights or deploy private instances of Google Gemini / Anthropic models within their sovereign Google Cloud Platform (GCP) or AWS VPC. Contact your dedicated Technical Account Manager or open an Enterprise Support Ticket to initiate custom model provisioning and VPC peering.",
    source_url: "/faq/features/custom-models"
  },
  {
    doc_id: "faq-12",
    category: "Feature Request",
    title: "Audit Logs, Role-Based Access Control (RBAC), and Compliance",
    content: "SmartDesk AI is SOC 2 Type II, ISO 27001, and GDPR compliant. Enterprise administrators can review granular immutable audit logs tracking user logins, ticket edits, AI draft approvals, and API credential changes. Role-based access control allows assigning roles: Admin, Support Supervisor, Support Specialist, and Read-Only Observer.",
    source_url: "/faq/features/rbac-compliance"
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
      {
        code: "faq-02: Two-Factor Authentication (2FA) Setup and Recovery",
        link: "/faq/auth/2fa-recovery",
        doc_id: "faq-02",
        title: "Two-Factor Authentication (2FA) Setup and Recovery",
        source_url: "/faq/auth/2fa-recovery"
      },
      {
        code: "faq-01: How to Reset Your CloudDesk / SmartDesk Password",
        link: "/faq/auth/password-reset",
        doc_id: "faq-01",
        title: "How to Reset Your CloudDesk / SmartDesk Password",
        source_url: "/faq/auth/password-reset"
      }
    ],
    time: "10:01",
    feedbackGiven: null
  }
];

export function getRagResponse(question: string, workspaceId: number = 1): {
  text: string;
  bulletPoints: string[];
  citations: Citation[];
} {
  const q = question.toLowerCase();

  // 1. Workspace 2: Nha Khoa SmileCare
  if (workspaceId === 2) {
    if (q.includes("niềng") || q.includes("invisalign") || q.includes("mắc cài") || q.includes("trả góp")) {
      return {
        text: `Bác sĩ SmileCare Bot xin tư vấn về dịch vụ Chỉnh nha & Niềng răng tại phòng khám:`,
        bulletPoints: [
          "Niềng răng mắc cài kim loại tiêu chuẩn: 25.000.000đ - 35.000.000đ.",
          "Niềng răng trong suốt Invisalign (Mỹ): 60.000.000đ - 95.000.000đ tùy mức độ xô lệch.",
          "Chính sách trả góp 0% lãi suất: Chỉ cần thanh toán trước 30%, phần còn lại chia đều trong 12 - 18 tháng."
        ],
        citations: [
          {
            code: "Bảng giá SmileCare (Trang 1)",
            link: "#",
            doc_id: "doc-sc-01",
            title: "Bảng giá Dịch vụ & Chính sách Bảo hành SmileCare",
            source_url: "/docs/smilecare"
          }
        ]
      };
    }

    if (q.includes("implant") || q.includes("trụ") || q.includes("răng") || q.includes("cạo vôi") || q.includes("trám")) {
      return {
        text: `Bác sĩ SmileCare Bot xin gửi thông tin chi phí các dịch vụ nha khoa tổng quát và cấy ghép Implant:`,
        bulletPoints: [
          "Cạo vôi răng và đánh bóng siêu âm: 200.000đ / 2 hàm.",
          "Trám răng thẩm mỹ bằng Composite hạt Nano: 350.000đ - 500.000đ / răng.",
          "Cấy ghép Implant Dentium (Hàn Quốc): 14.500.000đ/răng (bảo hành 15 năm). Trụ Straumann (Thụy Sĩ): 28.000.000đ/răng (bảo hành trọn đời).",
          "Khám tư vấn và chụp phim X-quang Panorex miễn phí 100%."
        ],
        citations: [
          {
            code: "Bảng giá SmileCare (Trang 1)",
            link: "#",
            doc_id: "doc-sc-01",
            title: "Bảng giá Dịch vụ & Chính sách Bảo hành SmileCare",
            source_url: "/docs/smilecare"
          }
        ]
      };
    }

    return {
      text: `Bác sĩ SmileCare Bot xin chào quý khách! Hiện tại trong tài liệu nha khoa chưa có thông tin chính xác về câu hỏi "${question}".`,
      bulletPoints: [
        "Nha Khoa SmileCare là cơ sở y tế chuyên khoa răng hàm mặt (niềng răng, implant, bọc sứ, thẩm mỹ).",
        "Nếu quý khách cần tư vấn tình trạng răng miệng hoặc đặt lịch khám với bác sĩ chuyên khoa, quý khách có thể gửi câu hỏi thêm.",
        "Quý khách vui lòng bấm nút 'Gửi Ticket' để đội ngũ lễ tân và trợ lý nha khoa liên hệ tư vấn trực tiếp."
      ],
      citations: [
        {
          code: "Tài liệu Nha Khoa SmileCare",
          link: "#",
          doc_id: "doc-sc-general",
          title: "Sổ tay Dịch vụ Khách hàng SmileCare",
          source_url: "/docs/smilecare"
        }
      ]
    };
  }

  // 2. Workspace 3: Điện Máy TechStore
  if (workspaceId === 3) {
    if (q.includes("đổi trả") || q.includes("1 đổi 1") || q.includes("30 ngày") || q.includes("lỗi") || q.includes("hộp")) {
      return {
        text: `TechStore Advisor xin thông tin chính sách đổi mới và bảo hành tại chuỗi siêu thị Điện Máy TechStore:`,
        bulletPoints: [
          "Chính sách 1 ĐỔI 1 TRONG 30 NGÀY ĐẦU TIÊN hoàn toàn miễn phí nếu sản phẩm phát sinh lỗi phần cứng từ nhà sản xuất.",
          "Điều kiện tiếp nhận: Giữ nguyên vỏ hộp (không rách nát), đầy đủ phụ kiện kèm theo và máy không bị trầy xước cấn móp.",
          "Bảo hành điện tử thông qua Serial/IMEI, thời gian xử lý tối đa 15 ngày làm việc."
        ],
        citations: [
          {
            code: "Chính sách Đổi trả TechStore (Trang 1)",
            link: "#",
            doc_id: "doc-ts-01",
            title: "Chính sách Đổi trả và Bảo hành Chính hãng TechStore",
            source_url: "/docs/techstore"
          }
        ]
      };
    }

    return {
      text: `TechStore Advisor xin chào quý khách! Trong hệ thống chính sách điện máy chưa tìm thấy thông tin chính xác cho câu hỏi "${question}".`,
      bulletPoints: [
        "Hệ thống Điện Máy TechStore hỗ trợ thiết bị điện thoại, laptop, tablet, tivi và gia dụng thông minh.",
        "Quý khách có thể bấm 'Gửi Ticket' để nhân viên kỹ thuật hoặc tổng đài viên 1800 6060 hỗ trợ nhanh chóng."
      ],
      citations: [
        {
          code: "Chính sách TechStore",
          link: "#",
          doc_id: "doc-ts-general",
          title: "Chính sách Khách hàng TechStore",
          source_url: "/docs/techstore"
        }
      ]
    };
  }

  // 3. Workspace 1 (Default): SmartDesk Cloud Support
  if (q.includes("hoàn tiền") || q.includes("thanh toán") || q.includes("billing") || q.includes("tiền")) {
    return {
      text: `Dưới đây là thông tin tra cứu tự động về quy định hoàn tiền và xử lý lỗi thanh toán giao dịch:`,
      bulletPoints: [
        "Các giao dịch phát sinh lỗi Timeout trên cổng thanh toán (VNPAY/Momo/Stripe) được hệ thống tự động đối soát trong vòng 15-30 phút.",
        "Tiền sẽ được hoàn trả tự động vào tài khoản gốc từ 1 đến 3 ngày làm việc tùy thuộc vào ngân hàng phát hành.",
        "Nếu sau 2 giờ chưa nhận được hoàn tiền hoặc cập nhật gói, vui lòng tạo phiếu hỗ trợ đính kèm mã sao kê giao dịch."
      ],
      citations: [
        {
          code: "faq-06: Refund Policy and Cancellation Terms",
          link: "/faq/billing/refund-policy",
          doc_id: "faq-06",
          title: "Refund Policy and Cancellation Terms",
          source_url: "/faq/billing/refund-policy"
        },
        {
          code: "faq-05: Payment Methods, Invoices, and Tax Receipts",
          link: "/faq/billing/invoices-tax",
          doc_id: "faq-05",
          title: "Payment Methods, Invoices, and Tax Receipts",
          source_url: "/faq/billing/invoices-tax"
        }
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
        {
          code: "faq-07: API Rate Limits, HTTP 429 Errors, and Exponential Backoff",
          link: "/faq/tech/rate-limits-429",
          doc_id: "faq-07",
          title: "API Rate Limits, HTTP 429 Errors, and Exponential Backoff",
          source_url: "/faq/tech/rate-limits-429"
        },
        {
          code: "faq-08: Webhook Delivery Failures and Retry Policy",
          link: "/faq/tech/webhook-retries",
          doc_id: "faq-08",
          title: "Webhook Delivery Failures and Retry Policy",
          source_url: "/faq/tech/webhook-retries"
        }
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
        {
          code: "faq-04: Subscription Plans, Billing Cycles, and Upgrades",
          link: "/faq/billing/plans-and-cycles",
          doc_id: "faq-04",
          title: "Subscription Plans, Billing Cycles, and Upgrades",
          source_url: "/faq/billing/plans-and-cycles"
        },
        {
          code: "faq-12: Audit Logs, Role-Based Access Control (RBAC), and Compliance",
          link: "/faq/features/rbac-compliance",
          doc_id: "faq-12",
          title: "Audit Logs, Role-Based Access Control (RBAC), and Compliance",
          source_url: "/faq/features/rbac-compliance"
        }
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
      {
        code: "faq-01: How to Reset Your CloudDesk / SmartDesk Password",
        link: "/faq/auth/password-reset",
        doc_id: "faq-01",
        title: "How to Reset Your CloudDesk / SmartDesk Password",
        source_url: "/faq/auth/password-reset"
      },
      {
        code: "faq-10: Knowledge Base Document Sync: Notion, Confluence, and Zendesk",
        link: "/faq/features/kb-sync",
        doc_id: "faq-10",
        title: "Knowledge Base Document Sync: Notion, Confluence, and Zendesk",
        source_url: "/faq/features/kb-sync"
      }
    ]
  };
}


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

export const INITIAL_WORKSPACES: Workspace[] = [
  {
    id: 1,
    slug: "default",
    name: "SmartDesk Cloud Support",
    industry: "IT & SaaS",
    persona_name: "SmartDesk Assistant",
    tone_of_voice: "Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật.",
    business_rules: "Hỗ trợ xử lý sự cố tài khoản, phân quyền, tích hợp API, thanh toán định kỳ. Luôn bảo vệ an toàn thông tin khách hàng.",
    created_at: "2026-09-01T00:00:00Z"
  },
  {
    id: 2,
    slug: "smilecare",
    name: "Nha Khoa Thẩm Mỹ SmileCare",
    industry: "Y tế & Nha khoa",
    persona_name: "Bác sĩ SmileCare Bot",
    tone_of_voice: "Ân cần, chu đáo, đồng cảm, chuyên môn y khoa cao nhưng dễ hiểu.",
    business_rules: "Tư vấn niềng răng, bọc sứ, tẩy trắng, cấy ghép Implant. Báo giá dịch vụ minh bạch. Không đưa ra chỉ định thuốc kháng sinh khi chưa có đơn khám.",
    created_at: "2026-09-02T00:00:00Z"
  },
  {
    id: 3,
    slug: "techstore",
    name: "Hệ Thống Điện Máy TechStore",
    industry: "Bán lẻ thiết bị công nghệ",
    persona_name: "TechStore Advisor",
    tone_of_voice: "Năng động, nhiệt tình, rõ ràng về thông số kỹ thuật và chính sách.",
    business_rules: "Tư vấn điện thoại, laptop, phụ kiện. Hướng dẫn đổi trả 1 đổi 1 trong 30 ngày nếu lỗi kỹ thuật. Quy định trừ phí phụ kiện nếu mất hộp.",
    created_at: "2026-09-03T00:00:00Z"
  }
];

export const INITIAL_DOCUMENTS: DocumentItem[] = [
  {
    id: 1,
    workspace_id: 2,
    filename: "nha_khoa_smilecare_bang_gia_dich_vu.txt",
    file_type: "txt",
    file_size: 1420,
    status: "published",
    chunk_count: 3,
    created_at: "2026-09-20T08:30:00Z"
  },
  {
    id: 2,
    workspace_id: 3,
    filename: "dien_may_techstore_chinh_sach_doi_tra.txt",
    file_type: "txt",
    file_size: 1850,
    status: "published",
    chunk_count: 4,
    created_at: "2026-09-21T09:15:00Z"
  }
];

export const INITIAL_VERIFICATION_REPORTS: Record<number, VerificationReport> = {
  1: {
    id: 1,
    document_id: 1,
    workspace_id: 2,
    faithfulness_score: 0.95,
    status: "passed",
    created_at: "2026-09-20T08:35:00Z",
    items: [
      {
        id: 1,
        question: "Chi phí niềng răng mắc cài kim loại tại SmileCare là bao nhiêu?",
        ground_truth: "Trọn gói 25.000.000 VNĐ. Thời gian điều trị từ 18 đến 24 tháng. Hỗ trợ trả góp 0% lãi suất trong 12 tháng.",
        rag_answer: "Giá niềng răng mắc cài kim loại tại SmileCare là 25.000.000 VNĐ trọn gói, điều trị trong 18-24 tháng và có trả góp 0% trong 12 tháng.",
        score: 0.98,
        status: "passed",
        reason: "Câu trả lời hoàn toàn chính xác và đầy đủ các chính sách bảo hành, trả góp."
      },
      {
        id: 2,
        question: "Khách hàng có được miễn phí quét dấu răng 3D Invisalign không?",
        ground_truth: "Khách hàng được quét dấu răng 3D iTero miễn phí trong lần thăm khám đầu tiên khi tư vấn Invisalign.",
        rag_answer: "Đúng vậy, khách hàng được miễn phí quét dấu răng 3D bằng máy iTero ngay lần thăm khám đầu tiên.",
        score: 0.95,
        status: "passed",
        reason: "Xác nhận đúng chính sách thăm khám ban đầu."
      }
    ]
  },
  2: {
    id: 2,
    document_id: 2,
    workspace_id: 3,
    faithfulness_score: 0.92,
    status: "passed",
    created_at: "2026-09-21T09:20:00Z",
    items: [
      {
        id: 3,
        question: "Thời hạn đổi trả 1 đổi 1 tại TechStore là bao lâu?",
        ground_truth: "Quy định 1 đổi 1 trong 30 ngày đầu tiên nếu sản phẩm phát sinh lỗi phần cứng từ nhà sản xuất.",
        rag_answer: "TechStore áp dụng chính sách 1 đổi 1 trong 30 ngày đầu tiên đối với các lỗi phần cứng từ nhà sản xuất.",
        score: 0.96,
        status: "passed",
        reason: "Khớp hoàn toàn với quy định 30 ngày đổi mới."
      }
    ]
  }
};
