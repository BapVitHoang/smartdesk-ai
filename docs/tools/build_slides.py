"""Build formal Presentation Slides PPTX (docs/SLIDES.pptx) and PDF (docs/SLIDES.pdf).
Strictly 15 slides matching docs/PRESENTATION_AND_DEMO.md, using official roster facts.
Generates PPTX via python-pptx and PDF via ReportLab in Landscape 16:9 format.
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import pypdf

# 1. Register TrueType fonts for PDF
FONT_DIR = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Arial", os.path.join(FONT_DIR, "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(FONT_DIR, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", os.path.join(FONT_DIR, "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", os.path.join(FONT_DIR, "arialbi.ttf")))
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")

# Slide Content Data (15 slides)
SLIDES_DATA = [
    {
        "slide_num": 1,
        "title": "SMARTDESK AI",
        "subtitle": "Hệ Thống Trợ Lý Hỗ Trợ Khách Hàng Thông Minh & Tự Động Hóa Tri Thức Đa Doanh Nghiệp",
        "bullets": [
            "Môn học: Các Hệ thống AI Ứng dụng & Agentic Nâng cao (2026–2027)",
            "Thành viên thực hiện (Thông tin chính thức từ docs/TEAM_ROSTER.md):",
            "  • Ngô Việt Hoàng (MSSV: 23110020) — Dev B & Integrator (@BapVitHoang)",
            "  • Lê Nguyên (MSSV: 23110043) — Dev A (@TheOrijinnn)",
            "  • Tống Gia Khánh (MSSV: 23110032) — Dev C (@TKhanh)",
            "Báo cáo và tài liệu cuối kỳ được Hoàng tổng hợp với sự hỗ trợ của AI agent và được cả nhóm rà soát."
        ]
    },
    {
        "slide_num": 2,
        "title": "VẤN ĐỀ & ĐỘNG LỰC THỰC TẾ",
        "subtitle": "Những Thách Thức Lớn Trong Vận Hành Chăm Sóc Khách Hàng (CSKH)",
        "bullets": [
            "Áp lực quá tải câu hỏi lặp lại: Hơn 60% yêu cầu liên quan đến các chính sách quen thuộc (hoàn tiền, 2FA, đổi trả).",
            "Thời gian phản hồi đầu tiên (FRT) kéo dài: Trung bình từ 4 đến 12 giờ, gây giảm sút mức độ hài lòng khách hàng (CSAT).",
            "Rủi ro AI ảo giác (Hallucination): Chatbot thông thường tự ý bịa đặt chính sách bảo hành hoặc cam kết sai thời hạn SLA.",
            "Nguy cơ gián đoạn dịch vụ khi quá tải Cloud: Các hệ thống chỉ dựa vào một LLM Cloud dễ bị lỗi 429 Resource Exhausted làm tê liệt kênh hỗ trợ."
        ]
    },
    {
        "slide_num": 3,
        "title": "GIẢI PHÁP SMARTDESK AI",
        "subtitle": "Nền Tảng Tự Động Hóa Hỗ Trợ Khách Hàng Đa Doanh Nghiệp Toàn Diện",
        "bullets": [
            "Customer RAG Chatbot: Phản hồi độ trễ thấp (< 1,500ms) kèm trích dẫn nguồn minh bạch (Citation Badges) từng trang tài liệu.",
            "Active Knowledge Verification Studio: Quy trình 3 tác tử tự động kiểm định độ trung thực trước khi xuất bản tài liệu.",
            "AI Copilot Hỗ trợ Nhân viên: Tự động phân loại danh mục, tính cam kết SLA và soạn sẵn bản thảo trả lời tiếng Việt.",
            "Deterministic Non-AI Fallback: Bộ so khớp Okapi BM25 phi AI trên 12 FAQ chuẩn kết hợp mạch ngắt Cost-Guard Cooldown 60s."
        ]
    },
    {
        "slide_num": 4,
        "title": "12 USER STORIES & MA TRẬN TRUY VẾT (RTM)",
        "subtitle": "Bao Phủ Toàn Diện Khách Hàng, Hỗ Trợ Viên & Quản Trị Viên (REQ-24, REQ-25)",
        "bullets": [
            "12 User Stories chuẩn mực (US-01 đến US-12) tuân thủ cấu trúc 'As a... I want... So that...' kèm tiêu chí chấp nhận cụ thể.",
            "Khách hàng: US-01 (RAG Q&A), US-02 (BM25 Fallback), US-04 (Tạo Ticket & SLA), US-12 (SSE Streaming & Thẻ xác nhận 2 pha).",
            "Nhân viên CSKH: US-05 (AI Copilot Triage), US-06 (Sắp xếp, Lọc danh mục, Phân trang & Xóa ticket).",
            "Quản trị viên: US-07 (Workspaces đa tenant), US-08 (Nạp tài liệu PDF/MD), US-09 (Studio sát hạch), US-10 (Dual-Provider), US-11 (RBAC).",
            "Bảng Ma trận Truy vết Yêu cầu (RTM) 4 cột chuẩn hóa: 100% (42/42) yêu cầu được liên kết mã nguồn và kiểm thử thành công."
        ]
    },
    {
        "slide_num": 5,
        "title": "KIẾN TRÚC TỔNG THỂ HỆ THỐNG",
        "subtitle": "Phân Tầng Hướng Dịch Vụ Phi Đồng Bộ (Async Architecture — REQ-26)",
        "bullets": [
            "Client Layer: React 19 + Vite 6 + Tailwind CSS v4 SPA. Tách biệt hoàn toàn qua API, tốc độ build ~2s, gói bundle gọn nhẹ (< 420 KB).",
            "Gateway Layer: FastAPI 100% Async ASGI, JWT HS256 Guard, Regex Gateway chặn Prompt Injection trong 0.05ms, mặt nạ hóa PII.",
            "Core Engine: RAG Orchestrator phân lập workspace, Copilot Structured Output, 4 Agent Tools với PendingAction, 3-Agent Studio.",
            "Dual AI Layer: Google Gemini 3.5 Flash Lite + Local Ollama Qwen2.5 3B + Okapi BM25 Non-AI Fallback.",
            "Persistence Layer: PostgreSQL 16 pgvector (<=> cosine distance) trong Docker, tự động fallback sang SQLite async khi dev local."
        ]
    },
    {
        "slide_num": 6,
        "title": "QUYẾT ĐỊNH THIẾT KẾ KIẾN TRÚC (ADR-001..004)",
        "subtitle": "Các Architecture Decision Records Nền Tảng (REQ-27)",
        "bullets": [
            "ADR-001: Dual AI Provider & Deterministic BM25 Fallback — 3 nấc bảo đảm 100% tính sẵn sàng dịch vụ.",
            "ADR-002: Dual-Engine Vector Store (PostgreSQL pgvector + SQLite) — Tối ưu cho Production đồng thời thân thiện cho Local Dev.",
            "ADR-003: 3-Agent Active Knowledge Verification Studio — Kiểm định độ trung thực tài liệu trước khi nạp vào RAG (ngưỡng >= 85%).",
            "ADR-004: Kiến trúc Frontend SPA React 19 + Vite 6 Thay Vì Next.js 14 SSR — Giao diện CSKH stateful, phản hồi streaming mượt mà."
        ]
    },
    {
        "slide_num": 7,
        "title": "MÔ HÌNH AI & QUẢN TRỊ PROMPT TẬP TRUNG",
        "subtitle": "Tối Ưu Hóa Độ Trễ, Chi Phí & Tính Riêng Tư Đa Doanh Nghiệp (REQ-18, REQ-19)",
        "bullets": [
            "Primary Cloud LLM: Google Gemini GA gemini-3.5-flash-lite (thinking_budget=0, temperature=0.2), độ trễ < 1,200ms.",
            "Mô hình Nhúng Chuẩn hóa: gemini-embedding-001 (768 chiều), tương thích hoàn hảo với nomic-embed-text của Ollama.",
            "Quản lý Prompt Tập trung: Toàn bộ system prompts được phiên bản hóa trong backend/data/prompts.json và quản lý bằng Git.",
            "Đa Persona theo Workspace: IT SaaS Enterprise (chuẩn mực), Nha Khoa SmileCare (thấu cảm y khoa), Điện Máy TechStore (đổi trả 30 ngày)."
        ]
    },
    {
        "slide_num": 8,
        "title": "BỐN AGENT TOOLS & THẺ XÁC NHẬN 2 PHA",
        "subtitle": "Mở Rộng Năng Lực Tác Tử AI Có Kiểm Soát An Toàn (Capability B — REQ-14)",
        "bullets": [
            "Tác tử AI hỗ trợ 4 công cụ thực tế: lookup_customer_tickets, create_escalation_ticket, update_ticket_priority_or_status, search_workspace_knowledge.",
            "Cơ chế Xác Nhận 2 Pha (Two-Phase Execution): Các hành động thay đổi dữ liệu (tạo hoặc đổi ticket) không tự ý thực thi ngay.",
            "Hệ thống sinh ra PendingAction với action_id duy nhất và hiển thị Thẻ Xác Nhận Thao Tác (Confirmation Card) trên màn hình chat.",
            "Chỉ khi người dùng nhấp [Xác nhận thực thi], Backend mới chính thức ghi dữ liệu, ngăn ngừa thao tác nhầm lẫn do AI suy luận."
        ]
    },
    {
        "slide_num": 9,
        "title": "PYDANTIC V2 STRUCTURED OUTPUT",
        "subtitle": "Chuẩn Hóa Dữ Liệu Ticket Triage Bằng Schema Nghiêm Ngặt (Capability C — REQ-15)",
        "bullets": [
            "Toàn bộ kết quả phân loại ticket của AI Copilot được ép kiểu nghiêm ngặt bằng schema TicketCopilotStructuredOutput.",
            "Chuẩn hóa 5 danh mục: Authentication, Billing, Bug Report (chuẩn hóa từ Technical Bug), Feature Request, General.",
            "Tính cam kết thời hạn SLA chuẩn xác: Urgent (2 giờ), High (4 giờ), Medium (8 giờ), Low (24 giờ).",
            "Tự động sinh 1–4 nhãn nhận diện (ai_tags), điểm tin cậy (confidence) và bản thảo câu trả lời tiếng Việt (ai_draft_reply)."
        ]
    },
    {
        "slide_num": 10,
        "title": "STUDIO SÁT HẠCH TRI THỨC 3 TÁC TỬ",
        "subtitle": "Active Knowledge Verification Studio Trước Khi Xuất Bản (Capability E — REQ-17)",
        "bullets": [
            "Tác tử 1 — Synthetic QA Exam Agent: Đọc tài liệu và tự động sinh tập câu hỏi - câu trả lời thử thách thực tế.",
            "Tác tử 2 — Sandbox RAG Runner: Gửi các câu hỏi thử thách vào pipeline RAG cô lập để trích xuất câu trả lời.",
            "Tác tử 3 — Faithfulness Judge Agent: Đối soát câu trả lời với văn bản nguồn để chấm điểm độ trung thực (Faithfulness Score).",
            "Chỉ các tài liệu đạt điểm trung thực >= 85% mới được cấp phép xuất bản (published) vào cơ sở tri thức phục vụ khách hàng."
        ]
    },
    {
        "slide_num": 11,
        "title": "AN TOÀN BẢO MẬT & QUYỀN RIÊNG TƯ DỮ LIỆU",
        "subtitle": "Hàng Rào Chắn Prompt Injection & Chính Sách Ẩn Danh PII (REQ-20, REQ-37)",
        "bullets": [
            "Hàng rào Prompt Injection Song ngữ: Hàm check_prompt_injection quét regex phát hiện jailbreak cả Tiếng Anh và Tiếng Việt.",
            "Chặn đứng tại Gateway trong 0.05ms với mã HTTP 400 (PROMPT_SECURITY_VIOLATION), không tốn token gọi mô hình.",
            "Chính sách Ẩn danh Thông tin Cá nhân: Hàm redact_pii tự động làm mờ Email, Số điện thoại VN và CCCD/CMND thành [REDACTED_*].",
            "Dữ liệu khách hàng được làm mờ triệt để trước khi truyền tải đến mô hình nhúng và Google Gemini Cloud."
        ]
    },
    {
        "slide_num": 12,
        "title": "COST-GUARD CIRCUIT BREAKER & BM25 FALLBACK",
        "subtitle": "Bảo Đảm Tính Sẵn Sàng 100% Khi LLM Gặp Sự Cố (REQ-20, REQ-23)",
        "bullets": [
            "Cost-Guard Circuit Breaker: Tự động kích hoạt khi gọi Gemini bị timeout > 4.0s hoặc trả về mã lỗi HTTP 429 Resource Exhausted.",
            "Hệ thống tự động khóa cổng gọi Cloud trong 60 giây (FREE_TIER_RATE_LIMIT_COOLDOWN) và chuyển sang Okapi BM25 cục bộ.",
            "Dự phòng phi AI mượt mà: Truy xuất câu trả lời phù hợp nhất từ 12 bài viết FAQ chuẩn trong seed_faq.json chỉ trong 12–18ms.",
            "Hiển thị thông báo minh bạch, banner đề xuất tạo ticket khẩn cấp, và cung cấp nút mở khóa Cooldown trên Telemetry Dashboard."
        ]
    },
    {
        "slide_num": 13,
        "title": "KẾT QUẢ THỰC NGHIỆM BỘ 24 TEST CASES",
        "subtitle": "Đột Phá Hiệu Năng Từ Baseline 33.3% Lên 100.0% (REQ-21, REQ-22)",
        "bullets": [
            "Bộ dữ liệu đánh giá chuẩn gồm 24 kịch bản (10 Normal, 6 Edge, 8 Should-Refuse) công khai minh bạch (0 held-out cases).",
            "Tỷ lệ đạt ban đầu (Baseline): 8 / 24 (33.3%) do thiếu hybrid retrieval, chưa có regex Tiếng Việt và lỗi phân tích cú pháp JSON thô.",
            "Tỷ lệ sau tối ưu (Upgraded): 24 / 24 (100.0%) — Tăng trưởng ngoạn mục +66.7% (+16 test cases đạt chuẩn).",
            "Bộ kiểm thử tự động Pytest: 139 passed, 2 skipped trong 56.94 giây; chi phí trung bình cực thấp (~$0.00021 USD / truy vấn)."
        ]
    },
    {
        "slide_num": 14,
        "title": "BẢO MẬT JWT HS256 & PHÂN QUYỀN RBAC",
        "subtitle": "Kiểm Soát Quyền Hạn & Cô Lập Dữ Liệu Khách Hàng Tuyệt Đối (REQ-09, REQ-36)",
        "bullets": [
            "Hệ thống xác thực Bearer JWT HS256 có thời hạn và khóa mã hóa bí mật lưu trong backend/.env.",
            "Phân quyền 2 vai trò chuẩn: admin (Toàn quyền quản trị, triage ticket, sát hạch tri thức) và user (Khách hàng thông thường).",
            "Cô lập dữ liệu nghiêm ngặt: Khách hàng chỉ xem được các ticket do chính email của mình tạo ra (0% rò rỉ dữ liệu).",
            "Giao diện Frontend tự động ẩn và khóa các tab Agent Dashboard và Knowledge Studio khi đăng nhập dưới vai trò user."
        ]
    },
    {
        "slide_num": 15,
        "title": "KẾT LUẬN & ĐỊNH HƯỚNG TƯƠNG LAI",
        "subtitle": "Tổng Kết Đóng Góp, Quyết Định Phạm Vi & Lộ Trình Phát Triển",
        "bullets": [
            "Tổng kết thành tựu: Xây dựng trọn vẹn nền tảng CSKH thông minh đáp ứng 100% 42 yêu cầu chuẩn mực và 12 User Stories.",
            "Ghi nhận giới hạn phạm vi REQ-16: Nhóm tập trung nguồn lực xây dựng 4 năng lực AI cốt lõi (A, B, C, E), quyết định không chọn năng lực D.",
            "Khắc phục triệt để tồn đọng MRG-DEF-01: Rebuild slide tự động chuẩn hóa nhân sự; giải quyết lệch chiều vector đám mây MRG-DEF-10.",
            "Định hướng tương lai: Tích hợp Gemini 2.0 Flash Vision đọc biểu đồ PDF, BGE-Reranker nâng cao độ chính xác và kết nối đa kênh Omnichannel."
        ]
    }
]


def build_pptx(filename="docs/SLIDES.pptx"):
    prs = Presentation()
    # 16:9 widescreen: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    for item in SLIDES_DATA:
        slide = prs.slides.add_slide(blank_layout)

        # Background color
        background = slide.background
        fill = background.fill
        fill.solid()
        if item["slide_num"] == 1:
            fill.fore_color.rgb = RGBColor(30, 58, 138)  # Deep Indigo #1E3A8A
        else:
            fill.fore_color.rgb = RGBColor(248, 250, 252) # Light Slate #F8FAFC

        # Header / Title Box
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.733), Inches(1.5))
        tf = title_box.text_frame
        tf.word_wrap = True

        p_title = tf.paragraphs[0]
        p_title.text = item["title"]
        p_title.font.name = "Arial"
        p_title.font.size = Pt(28 if item["slide_num"] == 1 else 24)
        p_title.font.bold = True
        if item["slide_num"] == 1:
            p_title.font.color.rgb = RGBColor(255, 255, 255)
        else:
            p_title.font.color.rgb = RGBColor(30, 64, 175) # #1E40AF

        p_sub = tf.add_paragraph()
        p_sub.text = item["subtitle"]
        p_sub.font.name = "Arial"
        p_sub.font.size = Pt(14)
        if item["slide_num"] == 1:
            p_sub.font.color.rgb = RGBColor(224, 231, 255)
        else:
            p_sub.font.color.rgb = RGBColor(75, 85, 99)

        # Content Box
        content_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.733), Inches(4.5))
        ctf = content_box.text_frame
        ctf.word_wrap = True

        for idx, bullet in enumerate(item["bullets"]):
            p = ctf.add_paragraph() if idx > 0 else ctf.paragraphs[0]
            p.text = bullet
            p.font.name = "Arial"
            p.font.size = Pt(13.5 if item["slide_num"] == 1 else 13)
            p.space_after = Pt(10)
            if item["slide_num"] == 1:
                p.font.color.rgb = RGBColor(241, 245, 249)
            else:
                p.font.color.rgb = RGBColor(31, 41, 55)

        # Slide Number in footer
        if item["slide_num"] > 1:
            footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.8), Inches(11.733), Inches(0.4))
            ftf = footer_box.text_frame
            fp = ftf.paragraphs[0]
            fp.text = f"SmartDesk AI — Bảo Vệ Đồ Án Cuối Kỳ | Slide {item['slide_num']} / 15"
            fp.font.name = "Arial"
            fp.font.size = Pt(9)
            fp.font.color.rgb = RGBColor(156, 163, 175)

    prs.save(filename)
    print(f"Generated {filename} successfully with {len(prs.slides)} slides.")


def build_pdf_slides(filename="docs/SLIDES.pdf"):
    # 16:9 Landscape page size: 841.89 x 473.56 pt (A4 width, 16:9 height)
    slide_pagesize = (842, 474)

    doc = SimpleDocTemplate(
        filename,
        pagesize=slide_pagesize,
        leftMargin=40,
        rightMargin=40,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()

    slide_title_dark = ParagraphStyle(
        "SlideTitleDark",
        fontName="Arial-Bold",
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#FFFFFF"),
        spaceAfter=6
    )
    slide_sub_dark = ParagraphStyle(
        "SlideSubDark",
        fontName="Arial",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#E0E7FF"),
        spaceAfter=20
    )
    slide_bullet_dark = ParagraphStyle(
        "SlideBulletDark",
        fontName="Arial",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#F8FAFC"),
        spaceAfter=8,
        leftIndent=15
    )

    slide_title_light = ParagraphStyle(
        "SlideTitleLight",
        fontName="Arial-Bold",
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#1E40AF"),
        spaceAfter=4
    )
    slide_sub_light = ParagraphStyle(
        "SlideSubLight",
        fontName="Arial",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=14
    )
    slide_bullet_light = ParagraphStyle(
        "SlideBulletLight",
        fontName="Arial",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=8,
        leftIndent=15
    )

    story = []

    for item in SLIDES_DATA:
        if item["slide_num"] == 1:
            # Dark title slide
            story.append(Paragraph(item["title"], slide_title_dark))
            story.append(Paragraph(item["subtitle"], slide_sub_dark))
            story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3B82F6"), spaceBefore=0, spaceAfter=15))
            for b in item["bullets"]:
                story.append(Paragraph(b, slide_bullet_dark))
        else:
            # Light content slide
            story.append(Paragraph(f"{item['slide_num']}. {item['title']}", slide_title_light))
            story.append(Paragraph(item["subtitle"], slide_sub_light))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563EB"), spaceBefore=0, spaceAfter=12))
            for b in item["bullets"]:
                story.append(Paragraph(f"• {b}", slide_bullet_light))

        if item["slide_num"] < 15:
            story.append(PageBreak())

    # Custom canvas for background & slide numbers
    class SlideCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def showPage(self):
            self.saveState()
            if self._pageNumber == 1:
                # Deep Indigo background for title slide
                self.setFillColor(colors.HexColor("#1E3A8A"))
                self.rect(0, 0, 842, 474, fill=1, stroke=0)
            else:
                # Light background for content slides
                self.setFillColor(colors.HexColor("#F8FAFC"))
                self.rect(0, 0, 842, 474, fill=1, stroke=0)
                # Footer
                self.setFont("Arial", 8)
                self.setFillColor(colors.HexColor("#9CA3AF"))
                self.drawString(40, 20, "SmartDesk AI — Bảo Vệ Đồ Án Cuối Kỳ | Advanced Agentic & Applied AI Systems")
                self.drawRightString(802, 20, f"Slide {self._pageNumber} / 15")
            self.restoreState()
            super().showPage()

    doc.build(story, canvasmaker=SlideCanvas)

    reader = pypdf.PdfReader(filename)
    num_pages = len(reader.pages)
    print(f"Generated {filename} successfully with {num_pages} pages.")

    if num_pages <= 15:
        print(f"[PASS] Slide count {num_pages} satisfies <= 15 requirement (REQ-41).")
    else:
        print(f"[FAIL] Slide count {num_pages} exceeds 15 slides limit.")
        sys.exit(1)


def main():
    build_pptx()
    build_pdf_slides()

if __name__ == "__main__":
    main()
