import React from 'react';
import { 
  Sparkles, 
  RotateCcw, 
  ShieldCheck, 
  Send, 
  Loader2, 
  Inbox 
} from 'lucide-react';
import { Ticket, TicketStatus, UIState } from '../../types';

interface TicketDetailProps {
  selectedTicket: Ticket | null;
  demoState: UIState;
  agentReplyText: string;
  setAgentReplyText: (text: string) => void;
  isRegeneratingDraft: boolean;
  agentSending: boolean;
  onRegenerateDraft: () => void;
  onStatusChange: (status: TicketStatus) => void;
  onSendReply: () => void;
  onResetOriginalDraft: () => void;
}

export const TicketDetail: React.FC<TicketDetailProps> = ({
  selectedTicket,
  demoState,
  agentReplyText,
  setAgentReplyText,
  isRegeneratingDraft,
  agentSending,
  onRegenerateDraft,
  onStatusChange,
  onSendReply,
  onResetOriginalDraft,
}) => {
  if (!selectedTicket || demoState === 'empty') {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm space-y-2">
        <Inbox className="w-10 h-10 text-slate-300" />
        <span>Chọn một ticket từ danh sách bên trái để xem chi tiết và duyệt bản thảo AI.</span>
      </div>
    );
  }

  return (
    <div className="max-w-3xl w-full mx-auto space-y-5">
      {/* Ticket Header Details */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-extrabold bg-slate-900 text-white px-2.5 py-1 rounded-lg">
              #{selectedTicket.id}
            </span>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                selectedTicket.priority === 'Urgent'
                  ? 'bg-rose-100 text-rose-800 border border-rose-300'
                  : selectedTicket.priority === 'High'
                  ? 'bg-orange-100 text-orange-800 border border-orange-300'
                  : 'bg-blue-100 text-blue-800'
              }`}
            >
              Priority: {selectedTicket.priority}
            </span>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              {selectedTicket.category}
            </span>
          </div>

          <div className="text-xs text-slate-500">
            Thời gian gửi: <span className="font-medium text-slate-700">{selectedTicket.date}</span>
          </div>
        </div>

        <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-3">
          {selectedTicket.subject}
        </h2>

        {/* Customer profile card */}
        <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-xs">
              {selectedTicket.customer.charAt(0)}
            </div>
            <div>
              <div className="font-bold text-slate-800">{selectedTicket.customer}</div>
              <div className="text-slate-500">{selectedTicket.email}</div>
            </div>
          </div>
          <span className="text-indigo-600 font-medium bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200/60 inline-flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
            Verified User
          </span>
        </div>

        {/* Customer Raw Message */}
        <div className="mt-4">
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
            Nội dung sự cố từ khách hàng:
          </h4>
          <div className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-xl text-xs sm:text-sm text-slate-800 leading-relaxed">
            {selectedTicket.message}
          </div>
        </div>
      </div>

      {/* AI Tóm Tắt Sự Cố & Context Engine */}
      <div className="bg-gradient-to-r from-indigo-950 via-indigo-900 to-slate-950 text-white rounded-2xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-200">
              SmartDesk AI Analysis
            </span>
          </div>
          <span className="text-[11px] bg-indigo-800/80 px-2.5 py-0.5 rounded text-indigo-100 font-mono border border-indigo-700/60">
            Confidence Score: 98.4%
          </span>
        </div>
        <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
          {selectedTicket.summary}
        </p>
      </div>

      {/* AI SUGGESTED DRAFT REPLY */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-bold">
              <Sparkles className="w-4 h-4 text-indigo-600" />
            </div>
            <h3 className="font-bold text-slate-800 text-sm sm:text-base">AI Suggested Draft Reply</h3>
          </div>
          <span className="text-xs text-slate-400 italic">Agent có thể chỉnh sửa trước khi gửi</span>
        </div>

        <div className="relative">
          <textarea
            id="agent-reply-textarea"
            rows={4}
            value={agentReplyText}
            onChange={(e) => setAgentReplyText(e.target.value)}
            className="w-full p-3.5 text-xs sm:text-sm rounded-xl border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 text-slate-800 bg-white focus:outline-none transition-all leading-relaxed"
            placeholder="Nhập hoặc hiệu chỉnh nội dung phản hồi gửi đến khách hàng..."
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
            <button
              type="button"
              id="btn-regenerate-ai-draft"
              disabled={isRegeneratingDraft}
              onClick={onRegenerateDraft}
              className="px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold border border-indigo-200 transition-colors inline-flex items-center gap-1.5 shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {isRegeneratingDraft ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                  <span>Đang sinh lại bản thảo...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Tạo lại AI Draft (Copilot)</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onResetOriginalDraft}
              className="text-slate-500 hover:text-slate-800 font-medium underline inline-flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Khôi phục bản thảo gốc</span>
            </button>

            <span>•</span>

            <div className="inline-flex items-center gap-1.5">
              <span className="text-slate-500">Trạng thái:</span>
              <select
                id="agent-ticket-status-select"
                value={selectedTicket.status}
                onChange={(e) => onStatusChange(e.target.value as TicketStatus)}
                className={`text-xs font-bold px-2.5 py-1 rounded-lg border focus:outline-none transition-colors cursor-pointer ${
                  selectedTicket.status === 'Open'
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                    : selectedTicket.status === 'Pending'
                    ? 'bg-amber-50 text-amber-800 border-amber-300'
                    : 'bg-slate-100 text-slate-700 border-slate-300'
                }`}
              >
                <option value="Open">Open</option>
                <option value="Pending">Pending</option>
                <option value="Resolved">Resolved</option>
              </select>
            </div>
          </div>

          <button
            id="btn-send-agent-reply"
            onClick={onSendReply}
            disabled={agentSending || !agentReplyText.trim()}
            className={`px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center gap-2 transition-all cursor-pointer ${
              agentSending
                ? 'bg-indigo-400 text-white cursor-wait'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-100 active:scale-95'
            }`}
          >
            {agentSending ? (
              <>
                <Loader2 className="w-4 h-4 text-white animate-spin" />
                <span>Đang gửi phản hồi...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Send Response &amp; Mark Resolved</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
