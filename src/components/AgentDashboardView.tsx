import React, { useState, useEffect } from 'react';
import { 
  Inbox, 
  Send, 
  Sparkles, 
  RotateCcw, 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  User, 
  ShieldCheck, 
  Tag, 
  Filter,
  Loader2
} from 'lucide-react';
import { Ticket, UIState, TicketStatus, ToastType } from '../types';
import { getTickets, updateTicketStatus, regenerateAiDraft } from '../services/api';

interface AgentDashboardViewProps {
  tickets: Ticket[];
  setTickets?: React.Dispatch<React.SetStateAction<Ticket[]>>;
  selectedTicket: Ticket | null;
  setSelectedTicket: (ticket: Ticket) => void;
  demoState: UIState;
  setDemoState: (state: UIState) => void;
  onUpdateTicketStatus: (ticketId: string, newStatus: TicketStatus, draftReply?: string) => void;
  onToast: (msg: string, type?: ToastType) => void;
}

export const AgentDashboardView: React.FC<AgentDashboardViewProps> = ({
  tickets,
  setTickets,
  selectedTicket,
  setSelectedTicket,
  demoState,
  setDemoState,
  onUpdateTicketStatus,
  onToast,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'open' | 'urgent'>('all');
  const [agentReplyText, setAgentReplyText] = useState(selectedTicket?.draftReply || '');
  const [agentSending, setAgentSending] = useState(false);
  const [isRegeneratingDraft, setIsRegeneratingDraft] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (selectedTicket) {
      setAgentReplyText(selectedTicket.draftReply);
    }
  }, [selectedTicket]);

  const filteredTickets = tickets.filter((t) => {
    if (filterType === 'open') return t.status === 'Open';
    if (filterType === 'urgent') return t.priority === 'Urgent';
    return true;
  });

  const handleRefreshTickets = async () => {
    setIsRefreshing(true);
    try {
      const fresh = await getTickets(undefined, onToast);
      if (setTickets && fresh && fresh.length > 0) {
        setTickets(fresh);
        if (!selectedTicket || !fresh.some((t) => t.id === selectedTicket.id)) {
          setSelectedTicket(fresh[0]);
        }
      }
      onToast('Đã cập nhật danh sách ticket từ máy chủ!', 'success');
    } catch {
      onToast('Không thể làm mới danh sách ticket.', 'warning');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleStatusChange = async (newStatus: TicketStatus) => {
    if (!selectedTicket || selectedTicket.status === newStatus) return;
    try {
      const updated = await updateTicketStatus(selectedTicket.id, newStatus, agentReplyText, onToast);
      onUpdateTicketStatus(selectedTicket.id, newStatus, agentReplyText);
      setSelectedTicket(updated);
      onToast(`Đã cập nhật trạng thái #${selectedTicket.id} sang ${newStatus}!`, 'info');
    } catch {
      onUpdateTicketStatus(selectedTicket.id, newStatus, agentReplyText);
    }
  };

  const handleSendAgentReply = async () => {
    if (!selectedTicket || !agentReplyText.trim()) return;

    setAgentSending(true);
    try {
      const updated = await updateTicketStatus(selectedTicket.id, 'Resolved', agentReplyText, onToast);
      onUpdateTicketStatus(selectedTicket.id, 'Resolved', agentReplyText);
      setSelectedTicket(updated);
      onToast(`Đã gửi phản hồi đến ${selectedTicket.customer} (#${selectedTicket.id}) và đánh dấu Resolved!`, 'success');
    } catch {
      onUpdateTicketStatus(selectedTicket.id, 'Resolved', agentReplyText);
      onToast(`Đã gửi phản hồi cho #${selectedTicket.id} và đánh dấu Resolved!`, 'success');
    } finally {
      setAgentSending(false);
    }
  };

  const handleRegenerateDraft = async () => {
    if (!selectedTicket || isRegeneratingDraft) return;

    setIsRegeneratingDraft(true);
    try {
      const updated = await regenerateAiDraft(selectedTicket.id, onToast);
      setAgentReplyText(updated.draftReply);
      setSelectedTicket(updated);
      onUpdateTicketStatus(selectedTicket.id, selectedTicket.status, updated.draftReply);
      onToast(`Đã tạo lại AI Draft thành công từ Copilot cho #${selectedTicket.id}!`, 'success');
    } catch {
      onToast('Không thể tạo lại AI Draft. Vui lòng thử lại.', 'error');
    } finally {
      setIsRegeneratingDraft(false);
    }
  };

  return (
    <div id="screen-agent-dashboard" className="flex-1 flex flex-col md:flex-row h-full overflow-hidden">
      
      {/* CỘT TRÁI: DANH SÁCH TICKET HOẶC TRẠNG THÁI SKELETON / EMPTY / ERROR */}
      <div className="w-full md:w-5/12 lg:w-4/12 border-r border-slate-200 bg-white flex flex-col h-full overflow-hidden shrink-0">
        
        {/* List Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
          <div>
            <h2 className="font-bold text-slate-900 text-sm sm:text-base">Hàng đợi Ticket (Triage Queue)</h2>
            <p className="text-xs text-slate-500">Phân loại &amp; gán nhãn tự động bởi SmartDesk</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefreshTickets}
              disabled={isRefreshing}
              title="Làm mới hàng đợi từ máy chủ"
              className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 bg-white transition-all shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
            </button>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-700">
              {demoState === 'empty' ? 0 : filteredTickets.length} tickets
            </span>
          </div>
        </div>

        {/* Filter Quick Tabs */}
        <div className="px-4 py-2 bg-white border-b border-slate-100 flex items-center gap-1 shrink-0 text-xs">
          <button
            onClick={() => setFilterType('all')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              filterType === 'all'
                ? 'bg-slate-900 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Tất cả
          </button>
          <button
            onClick={() => setFilterType('open')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              filterType === 'open'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Chưa xử lý (Open)
          </button>
          <button
            onClick={() => setFilterType('urgent')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all ${
              filterType === 'urgent'
                ? 'bg-rose-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Khẩn cấp (Urgent)
          </button>
        </div>

        {/* NỘI DUNG DANH SÁCH THEO 4 TRẠNG THÁI DEMO */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2.5 bg-slate-50/30">
          
          {/* TRẠNG THÁI 1: LOADING STATE (Skeleton Loaders) */}
          {demoState === 'loading' && (
            <div className="space-y-3 p-1">
              {[1, 2, 3, 4].map((n) => (
                <div key={n} className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-2.5 animate-pulse">
                  <div className="flex justify-between items-center">
                    <div className="h-4 w-20 bg-slate-200 rounded"></div>
                    <div className="h-4 w-16 bg-slate-200 rounded-full"></div>
                  </div>
                  <div className="h-4 w-4/5 bg-slate-300 rounded"></div>
                  <div className="h-3 w-3/5 bg-slate-200 rounded"></div>
                  <div className="flex gap-2 pt-1">
                    <div className="h-5 w-24 bg-slate-200 rounded"></div>
                    <div className="h-5 w-16 bg-slate-100 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TRẠNG THÁI 2: EMPTY STATE */}
          {demoState === 'empty' && (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
                <Inbox className="w-8 h-8" />
              </div>
              <div>
                <h4 className="font-bold text-slate-800 text-sm">Chưa có ticket nào trong hàng đợi</h4>
                <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
                  Hiện tại tất cả các yêu cầu từ khách hàng đều đã được AI giải quyết hoặc agent xử lý hoàn tất.
                </p>
              </div>
              <button
                onClick={async () => {
                  setDemoState('success');
                  await handleRefreshTickets();
                }}
                className="px-4 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200 transition-colors inline-flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Làm mới hàng đợi (Refresh)</span>
              </button>
            </div>
          )}

          {/* TRẠNG THÁI 3: ERROR STATE */}
          {demoState === 'error' && (
            <div className="p-2">
              <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-5 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-bold text-rose-900 text-sm">Không thể tải dữ liệu từ máy chủ</h4>
                  <p className="text-xs text-rose-700 mt-1">
                    (Simulated Network Error 503) – Đường truyền gateway gặp gián đoạn tạm thời.
                  </p>
                </div>
                <button
                  onClick={async () => {
                    setDemoState('success');
                    await handleRefreshTickets();
                  }}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs transition-colors inline-flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Thử lại (Retry Connection)</span>
                </button>
              </div>
            </div>
          )}

          {/* TRẠNG THÁI 4: SUCCESS STATE (HIỂN THỊ DANH SÁCH TICKETS) */}
          {demoState === 'success' && (
            filteredTickets.length > 0 ? (
              filteredTickets.map((t) => {
                const isSelected = selectedTicket?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedTicket(t)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer text-left ${
                      isSelected
                        ? 'bg-indigo-50/80 border-indigo-400 shadow-xs ring-1 ring-indigo-300'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">#{t.id}</span>
                        <span className="text-[11px] text-slate-400">• {t.date}</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          t.status === 'Open'
                            ? 'bg-emerald-100 text-emerald-800'
                            : t.status === 'Pending'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {t.status}
                      </span>
                    </div>

                    <h4 className="text-xs sm:text-sm font-semibold text-slate-800 line-clamp-1 mb-1">
                      {t.subject}
                    </h4>

                    <p className="text-xs text-slate-500 line-clamp-2 mb-2 leading-relaxed">
                      {t.summary}
                    </p>

                    <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                      <div className="flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-700 text-[10px] flex items-center justify-center font-bold">
                          {t.customer.charAt(0)}
                        </span>
                        <span className="text-slate-600 truncate max-w-[110px]">{t.customer}</span>
                      </div>

                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-100/70 text-indigo-800 text-[10px] font-semibold">
                        <Tag className="w-3 h-3 text-indigo-600" />
                        {t.aiTag}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-6 text-center text-xs text-slate-400">
                Không tìm thấy ticket nào phù hợp với bộ lọc hiện tại.
              </div>
            )
          )}

        </div>
      </div>

      {/* CỘT PHẢI: CHI TIẾT TICKET & AI SUGGESTED DRAFT REPLY */}
      <div className="flex-1 bg-slate-50/50 flex flex-col h-full overflow-y-auto custom-scrollbar p-4 sm:p-6">
        {selectedTicket && demoState !== 'empty' ? (
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
                    onClick={handleRegenerateDraft}
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
                    onClick={() => {
                      setAgentReplyText(selectedTicket.draftReply);
                      onToast('Đã khôi phục câu trả lời mẫu từ AI');
                    }}
                    className="text-slate-500 hover:text-slate-800 font-medium underline inline-flex items-center gap-1"
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
                      onChange={(e) => handleStatusChange(e.target.value as TicketStatus)}
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
                  onClick={handleSendAgentReply}
                  disabled={agentSending || !agentReplyText.trim()}
                  className={`px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center gap-2 transition-all ${
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
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm space-y-2">
            <Inbox className="w-10 h-10 text-slate-300" />
            <span>Chọn một ticket từ danh sách bên trái để xem chi tiết và duyệt bản thảo AI.</span>
          </div>
        )}
      </div>

    </div>
  );
};
