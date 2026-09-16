import React, { useState } from 'react';
import { 
  FileText, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Send, 
  Loader2,
  HelpCircle,
  ShieldCheck,
  Check,
  Sparkles
} from 'lucide-react';
import { 
  Ticket, 
  TicketFormData, 
  TicketFormErrors, 
  TicketPriority, 
  TicketCategory, 
  TabType,
  ToastType 
} from '../types';
import { createTicket } from '../services/api';

interface TicketFormViewProps {
  onTicketCreated: (newTicket: Ticket) => void;
  setActiveTab: (tab: TabType) => void;
  setSelectedTicket: (ticket: Ticket) => void;
  onToast: (msg: string, type?: ToastType) => void;
}

export const TicketFormView: React.FC<TicketFormViewProps> = ({
  onTicketCreated,
  setActiveTab,
  setSelectedTicket,
  onToast,
}) => {
  const [formData, setFormData] = useState<TicketFormData>({
    fullName: '',
    email: '',
    category: 'Authentication',
    priority: 'Medium',
    subject: '',
    message: '',
  });

  const [formErrors, setFormErrors] = useState<TicketFormErrors>({});
  const [formTouched, setFormTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ticketCreatedSuccess, setTicketCreatedSuccess] = useState<Ticket | null>(null);

  // SLA calculation helper
  const getSlaByPriority = (priority: TicketPriority) => {
    switch (priority) {
      case 'Urgent':
        return '2 giờ làm việc (Cam kết SLA P1)';
      case 'High':
        return '4 giờ làm việc (Cam kết SLA P2)';
      case 'Medium':
        return '8 giờ làm việc (Cam kết SLA P3)';
      case 'Low':
        return '24 giờ làm việc (Cam kết SLA P4)';
      default:
        return '8 giờ làm việc';
    }
  };

  const validateField = (name: keyof TicketFormData, value: string): string => {
    let error = '';
    if (name === 'fullName') {
      if (!value || !value.trim()) {
        error = 'Vui lòng nhập họ và tên (tối thiểu 2 ký tự)';
      } else if (value.trim().length < 2) {
        error = 'Vui lòng nhập họ và tên (tối thiểu 2 ký tự)';
      }
    }

    if (name === 'email') {
      // RFC compliant regex
      const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
      if (!value || !value.trim()) {
        error = 'Vui lòng nhập địa chỉ email hợp lệ, ví dụ: user@example.com';
      } else if (!emailRegex.test(value.trim())) {
        error = 'Vui lòng nhập địa chỉ email hợp lệ, ví dụ: user@example.com';
      }
    }

    if (name === 'category') {
      if (!value || !value.trim()) {
        error = 'Vui lòng chọn danh mục hỗ trợ';
      }
    }

    if (name === 'priority') {
      if (!value || !value.trim()) {
        error = 'Vui lòng chọn mức độ ưu tiên';
      }
    }

    if (name === 'subject') {
      if (!value || !value.trim()) {
        error = 'Tiêu đề sự cố cần có độ dài từ 5 đến 120 ký tự';
      } else if (value.trim().length < 5 || value.trim().length > 120) {
        error = 'Tiêu đề sự cố cần có độ dài từ 5 đến 120 ký tự';
      }
    }

    if (name === 'message') {
      if (!value || !value.trim()) {
        error = 'Vui lòng mô tả chi tiết sự cố (tối thiểu 15 ký tự)';
      } else if (value.trim().length < 15) {
        error = 'Vui lòng mô tả chi tiết sự cố (tối thiểu 15 ký tự)';
      } else if (value.length > 2000) {
        error = 'Nội dung vượt quá giới hạn tối đa 2000 ký tự';
      }
    }

    return error;
  };

  const handleBlur = (field: keyof TicketFormData) => {
    setFormTouched((prev) => ({ ...prev, [field]: true }));
    const error = validateField(field, formData[field]);
    setFormErrors((prev) => ({ ...prev, [field]: error }));
  };

  const handleInputChange = (field: keyof TicketFormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (formTouched[field]) {
      const error = validateField(field, value);
      setFormErrors((prev) => ({ ...prev, [field]: error }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const touchedAll = {
      fullName: true,
      email: true,
      category: true,
      priority: true,
      subject: true,
      message: true,
    };
    setFormTouched(touchedAll);

    const errors: TicketFormErrors = {
      fullName: validateField('fullName', formData.fullName),
      email: validateField('email', formData.email),
      category: validateField('category', formData.category),
      priority: validateField('priority', formData.priority),
      subject: validateField('subject', formData.subject),
      message: validateField('message', formData.message),
    };
    setFormErrors(errors);

    const hasError = Object.values(errors).some((err) => err && err.length > 0);
    if (hasError) {
      onToast('Vui lòng kiểm tra lại các trường báo lỗi màu đỏ!', 'error');
      return;
    }

    setIsSubmitting(true);

    try {
      const newTicketObj = await createTicket(formData, onToast);

      onTicketCreated(newTicketObj);
      setTicketCreatedSuccess(newTicketObj);
      onToast(`Tạo Ticket ${newTicketObj.ticket_code || '#' + newTicketObj.id} thành công!`, 'success');

      // Reset form
      setFormData({
        fullName: '',
        email: '',
        category: 'Authentication',
        priority: 'Medium',
        subject: '',
        message: '',
      });
      setFormTouched({});
      setFormErrors({});
    } catch (err: any) {
      onToast('Không thể tạo ticket. Vui lòng kiểm tra kết nối!', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="screen-ticket-form" className="flex-1 overflow-y-auto p-4 sm:p-6 custom-scrollbar">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Top Context Notification */}
        <div className="bg-gradient-to-r from-indigo-50 via-white to-indigo-50 border border-indigo-100 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Gửi Phiếu Hỗ Trợ Kỹ Thuật (Escalate Ticket)</h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Khi AI Chatbot không giải quyết được triệt để, thông tin sẽ được chuyển thẳng tới hàng đợi của bộ phận chuyên trách.
              </p>
            </div>
          </div>
          <button
            id="btn-goto-agent-from-ticket"
            onClick={() => setActiveTab('agent')}
            className="text-xs font-semibold text-indigo-700 bg-white hover:bg-indigo-50 px-3.5 py-2 rounded-lg border border-indigo-200 transition-colors shadow-xs whitespace-nowrap inline-flex items-center gap-1.5"
          >
            <span>Xem Hàng Đợi Ticket</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* BANNER TÓM TẮT QUY TẮC KIỂM TRA (Form Validation Rules Guide) */}
        <div className="bg-white border border-indigo-100 rounded-2xl p-4 sm:p-5 shadow-xs">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 font-bold text-xs">
                <ShieldCheck className="w-4 h-4" />
              </span>
              <h4 className="font-bold text-slate-900 text-sm">
                Bảng Quy Tắc Kiểm Tra Tính Hợp Lệ (Validation Rules Guide)
              </h4>
            </div>
            <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
              Kiểm tra OnBlur &amp; OnSubmit
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-600">
            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
                Họ tên &amp; Email
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                <strong>Họ tên:</strong> Bắt buộc, tối thiểu 2 ký tự.<br />
                <strong>Email:</strong> Bắt buộc, đúng chuẩn RFC (<code className="text-indigo-600 font-mono">user@example.com</code>).
              </p>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
                Danh mục &amp; Ưu tiên
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                <strong>Danh mục:</strong> Chọn 1 trong 4 danh mục hỗ trợ.<br />
                <strong>Ưu tiên:</strong> 4 pills (Low, Med, High, Urgent) kèm SLA tương ứng.
              </p>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-1">
              <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
                Tiêu đề &amp; Nội dung
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                <strong>Tiêu đề:</strong> Từ 5 đến 120 ký tự.<br />
                <strong>Mô tả:</strong> Tối thiểu 15 ký tự, tối đa 2000 ký tự có bộ đếm trực quan.
              </p>
            </div>
          </div>
        </div>

        {/* Success Banner if Ticket Created with SLA Commitment */}
        {ticketCreatedSuccess && (
          <div id="ticket-success-alert" className="bg-emerald-50 border border-emerald-300 rounded-2xl p-5 shadow-xs flex items-start justify-between">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-base shrink-0 shadow-xs">
                <Check className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h3 className="font-bold text-emerald-950 text-base">Gửi Ticket Thành Công!</h3>
                  <span className="font-mono bg-emerald-200/80 text-emerald-900 font-bold text-xs px-2.5 py-0.5 rounded-md border border-emerald-300">
                    {ticketCreatedSuccess.ticket_code || `#${ticketCreatedSuccess.id}`}
                  </span>
                  <span className="text-[11px] font-semibold bg-white text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-md">
                    Đã lưu hàng đợi Triage
                  </span>
                </div>

                <p className="text-xs text-emerald-900 mt-1.5 leading-relaxed">
                  Yêu cầu hỗ trợ về <strong>"{ticketCreatedSuccess.subject}"</strong> đã được chuyển giao thành công. Đội ngũ SmartDesk AI đã phân loại tự động và chuyển email xác nhận đến <strong>{ticketCreatedSuccess.email}</strong>.
                </p>

                {/* AI Triage Tags */}
                {ticketCreatedSuccess.ai_tags && ticketCreatedSuccess.ai_tags.length > 0 && (
                  <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
                    <span className="text-[11px] font-semibold text-emerald-950">AI Triage Tags:</span>
                    {ticketCreatedSuccess.ai_tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white border border-emerald-300 text-emerald-800 shadow-xs"
                      >
                        🏷️ {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Cam kết SLA Card */}
                <div className="mt-3 p-3 bg-white border border-emerald-200 rounded-xl flex items-center gap-2.5 text-xs text-emerald-800">
                  <Clock className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-bold text-emerald-950">Cam kết SLA phản hồi: </span>
                    <span>{ticketCreatedSuccess.slaTime} (Cấp độ {ticketCreatedSuccess.priority})</span>
                  </div>
                </div>

                {/* AI Draft Reply Preview */}
                {ticketCreatedSuccess.draftReply && (
                  <div className="mt-3 p-3 bg-white/95 border border-emerald-200 rounded-xl text-xs text-slate-700 space-y-1 shadow-xs">
                    <div className="text-[11px] font-bold text-emerald-950 flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Bản thảo phản hồi gợi ý bởi AI Copilot:</span>
                    </div>
                    <p className="line-clamp-3 text-slate-600 italic whitespace-pre-line leading-relaxed text-[11px]">
                      {ticketCreatedSuccess.draftReply}
                    </p>
                  </div>
                )}

                <div className="mt-4 flex flex-wrap gap-2.5">
                  <button
                    onClick={() => {
                      setSelectedTicket(ticketCreatedSuccess);
                      setActiveTab('agent');
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
                  >
                    <span>Xem Ticket trong Agent Dashboard</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setTicketCreatedSuccess(null)}
                    className="px-3.5 py-2 bg-white text-slate-700 text-xs font-medium rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors"
                  >
                    Đóng thông báo
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main Ticket Form Card */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex justify-between items-center">
            <div>
              <h3 className="font-bold text-slate-800 text-sm sm:text-base">Biểu mẫu yêu cầu hỗ trợ (Support Ticket Form)</h3>
              <p className="text-xs text-slate-500">Các trường đánh dấu (*) là bắt buộc và được kiểm tra hợp lệ tức thì onBlur &amp; onSubmit.</p>
            </div>
            <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2.5 py-1 rounded-full hidden sm:inline-block">
              Strict RFC Validation
            </span>
          </div>

          <form onSubmit={handleSubmit} noValidate className="p-6 space-y-5">
            {/* Grid 2 Cột: Name & Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              
              {/* Họ và tên */}
              <div>
                <label htmlFor="ticket-fullname" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Họ và tên khách hàng (Full Name) <span className="text-rose-500">*</span>
                </label>
                <input
                  id="ticket-fullname"
                  type="text"
                  value={formData.fullName}
                  placeholder="Ví dụ: Nguyễn Văn An"
                  onChange={(e) => handleInputChange('fullName', e.target.value)}
                  onBlur={() => handleBlur('fullName')}
                  className={`w-full px-3.5 py-2.5 text-sm rounded-xl border focus:outline-none transition-all ${
                    formTouched.fullName && formErrors.fullName
                      ? 'border-rose-500 bg-rose-50/30 text-slate-900 focus:ring-2 focus:ring-rose-400 focus:border-rose-500'
                      : 'border-slate-200 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800'
                  }`}
                />
                {formTouched.fullName && formErrors.fullName && (
                  <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                    <span>{formErrors.fullName}</span>
                  </p>
                )}
              </div>

              {/* Email */}
              <div>
                <label htmlFor="ticket-email" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Email liên hệ (Customer Email) <span className="text-rose-500">*</span>
                </label>
                <input
                  id="ticket-email"
                  type="email"
                  value={formData.email}
                  placeholder="an.nguyen@company.vn"
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  onBlur={() => handleBlur('email')}
                  className={`w-full px-3.5 py-2.5 text-sm rounded-xl border focus:outline-none transition-all ${
                    formTouched.email && formErrors.email
                      ? 'border-rose-500 bg-rose-50/30 text-slate-900 focus:ring-2 focus:ring-rose-400 focus:border-rose-500'
                      : 'border-slate-200 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800'
                  }`}
                />
                {formTouched.email && formErrors.email && (
                  <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                    <span>{formErrors.email}</span>
                  </p>
                )}
              </div>
            </div>

            {/* Grid 2 Cột: Category & Priority */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              
              {/* Danh mục (Category) */}
              <div>
                <label htmlFor="ticket-category" className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Danh mục sự cố (Category) <span className="text-rose-500">*</span>
                </label>
                <select
                  id="ticket-category"
                  value={formData.category}
                  onChange={(e) => handleInputChange('category', e.target.value as TicketCategory)}
                  onBlur={() => handleBlur('category')}
                  className={`w-full px-3.5 py-2.5 text-sm rounded-xl border transition-all focus:outline-none ${
                    formTouched.category && formErrors.category
                      ? 'border-rose-500 bg-rose-50/30 text-slate-900 focus:ring-2 focus:ring-rose-400'
                      : 'border-slate-200 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800'
                  }`}
                >
                  <option value="Authentication">Authentication (Đăng nhập, 2FA, OTP, Phân quyền)</option>
                  <option value="Billing">Billing (Thanh toán, Hoàn tiền, Xuất hóa đơn VAT)</option>
                  <option value="Bug Report">Bug Report (Lỗi giao diện, Crash ứng dụng, Timeout)</option>
                  <option value="Feature Request">Feature Request (Đề xuất tính năng, Yêu cầu API)</option>
                </select>
                {formTouched.category && formErrors.category && (
                  <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                    <span>{formErrors.category}</span>
                  </p>
                )}
              </div>

              {/* Mức độ ưu tiên (Priority) với 4 Pills trực quan */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    Mức độ ưu tiên (Priority) <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[11px] text-slate-500">
                    SLA: {formData.priority === 'Urgent' ? '2h' : formData.priority === 'High' ? '4h' : formData.priority === 'Medium' ? '8h' : '24h'}
                  </span>
                </div>
                
                <div className="grid grid-cols-4 gap-2">
                  {(['Low', 'Medium', 'High', 'Urgent'] as TicketPriority[]).map((lvl) => {
                    const isSelected = formData.priority === lvl;
                    let colorClass = 'text-slate-600 border-slate-200 bg-white hover:bg-slate-50';
                    if (isSelected) {
                      if (lvl === 'Low') colorClass = 'bg-blue-50 text-blue-700 border-blue-400 font-bold shadow-xs';
                      if (lvl === 'Medium') colorClass = 'bg-amber-50 text-amber-700 border-amber-400 font-bold shadow-xs';
                      if (lvl === 'High') colorClass = 'bg-orange-50 text-orange-700 border-orange-400 font-bold shadow-xs';
                      if (lvl === 'Urgent') colorClass = 'bg-rose-50 text-rose-700 border-rose-500 font-bold ring-2 ring-rose-400 shadow-xs';
                    }
                    return (
                      <button
                        type="button"
                        key={lvl}
                        onClick={() => handleInputChange('priority', lvl)}
                        className={`py-2 px-1 text-center rounded-xl border text-xs transition-all ${colorClass}`}
                      >
                        {lvl}
                      </button>
                    );
                  })}
                </div>
                {formTouched.priority && formErrors.priority && (
                  <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                    <span>{formErrors.priority}</span>
                  </p>
                )}
              </div>
            </div>

            {/* Tiêu đề (Subject) - Bắt buộc, 5 đến 120 ký tự */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label htmlFor="ticket-subject" className="block text-xs font-semibold text-slate-700">
                  Tiêu đề yêu cầu (Subject) <span className="text-rose-500">*</span>
                </label>
                <span
                  className={`text-[11px] ${
                    formData.subject.trim().length >= 5 && formData.subject.trim().length <= 120
                      ? 'text-emerald-600 font-medium'
                      : 'text-slate-400'
                  }`}
                >
                  {formData.subject.length}/120 ký tự (5-120)
                </span>
              </div>
              <input
                id="ticket-subject"
                type="text"
                value={formData.subject}
                placeholder="Mô tả ngắn gọn vấn đề (vd: Không thể thanh toán gói dịch vụ qua thẻ Visa)"
                onChange={(e) => handleInputChange('subject', e.target.value)}
                onBlur={() => handleBlur('subject')}
                maxLength={120}
                className={`w-full px-3.5 py-2.5 text-sm rounded-xl border focus:outline-none transition-all ${
                  formTouched.subject && formErrors.subject
                    ? 'border-rose-500 bg-rose-50/30 text-slate-900 focus:ring-2 focus:ring-rose-400 focus:border-rose-500'
                    : 'border-slate-200 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800'
                }`}
              />
              {formTouched.subject && formErrors.subject && (
                <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                  <span>{formErrors.subject}</span>
                </p>
              )}
            </div>

            {/* Chi tiết nội dung (Message / Description) - Tối thiểu 15 ký tự, tối đa 2000 ký tự với bộ đếm */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label htmlFor="ticket-message" className="block text-xs font-semibold text-slate-700">
                  Nội dung chi tiết (Description / Message) <span className="text-rose-500">*</span>
                </label>
                <span
                  className={`text-[11px] font-mono ${
                    formData.message.trim().length >= 15 && formData.message.length <= 2000
                      ? 'text-emerald-600 font-semibold'
                      : formData.message.length > 2000
                      ? 'text-rose-600 font-bold'
                      : 'text-slate-400'
                  }`}
                >
                  {formData.message.length}/2000 ký tự (tối thiểu 15)
                </span>
              </div>
              <textarea
                id="ticket-message"
                rows={4}
                value={formData.message}
                maxLength={2000}
                placeholder="Vui lòng mô tả chi tiết các bước xảy ra lỗi, mã giao dịch hoặc thông báo lỗi xuất hiện..."
                onChange={(e) => handleInputChange('message', e.target.value)}
                onBlur={() => handleBlur('message')}
                className={`w-full px-3.5 py-2.5 text-sm rounded-xl border focus:outline-none transition-all ${
                  formTouched.message && formErrors.message
                    ? 'border-rose-500 bg-rose-50/30 text-slate-900 focus:ring-2 focus:ring-rose-400 focus:border-rose-500'
                    : 'border-slate-200 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800'
                }`}
              />
              {formTouched.message && formErrors.message && (
                <p className="text-rose-600 text-xs mt-1 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
                  <span>{formErrors.message}</span>
                </p>
              )}
            </div>

            {/* Submit Action */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <div className="text-xs text-slate-500 hidden sm:flex items-center gap-2">
                <span>Mã ticket tự sinh:</span>
                <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-700 font-semibold">
                  #TICK-xxxx
                </code>
                <span>• SLA: {getSlaByPriority(formData.priority)}</span>
              </div>

              <button
                id="submit-ticket-button"
                type="submit"
                disabled={isSubmitting}
                className={`px-6 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all ${
                  isSubmitting
                    ? 'bg-indigo-400 text-white cursor-wait'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-100 active:scale-98'
                }`}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 text-white animate-spin" />
                    <span>Đang lập Ticket (Giả lập 1s)...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Submit Support Ticket</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
