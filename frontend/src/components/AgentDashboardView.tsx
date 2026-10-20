import React, { useState, useEffect } from 'react';
import { Ticket, UIState, TicketStatus, ToastType } from '../types';
import { getTickets, updateTicketStatus, regenerateAiDraft } from '../services/api';
import { TicketToolbar, TicketList, TicketDetail } from '../features/agent';

interface AgentDashboardViewProps {
  tickets: Ticket[];
  setTickets?: React.Dispatch<React.SetStateAction<Ticket[]>>;
  selectedTicket: Ticket | null;
  setSelectedTicket: (ticket: Ticket) => void;
  demoState: UIState;
  setDemoState: (state: UIState) => void;
  onUpdateTicketStatus: (ticketId: string, newStatus: TicketStatus, draftReply?: string) => void;
  onToast: (msg: string, type?: ToastType) => void;
  currentWorkspaceId?: number;
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
  currentWorkspaceId,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'open' | 'urgent'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [agentReplyText, setAgentReplyText] = useState(selectedTicket?.draftReply || '');
  const [agentSending, setAgentSending] = useState(false);
  const [isRegeneratingDraft, setIsRegeneratingDraft] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    if (selectedTicket) {
      setAgentReplyText(selectedTicket.draftReply);
    }
  }, [selectedTicket]);

  // Combined real-time filtering: Status + Category + Search term
  const filteredTickets = tickets.filter((t) => {
    // 1. Status / Urgency filter
    if (filterType === 'open' && t.status !== 'Open') return false;
    if (filterType === 'urgent' && t.priority !== 'Urgent') return false;

    // 2. Category filter
    if (selectedCategory !== 'all' && t.category !== selectedCategory) {
      return false;
    }

    // 3. Search query: Ticket ID, customer name, or subject
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      const idMatch =
        t.id.toLowerCase().includes(term) ||
        (t.ticket_code && t.ticket_code.toLowerCase().includes(term));
      const customerMatch = t.customer.toLowerCase().includes(term);
      const subjectMatch = t.subject.toLowerCase().includes(term);
      if (!idMatch && !customerMatch && !subjectMatch) return false;
    }

    return true;
  });

  const handleRefreshTickets = async () => {
    setIsRefreshing(true);
    try {
      const filters: {
        status?: string;
        category?: string;
        priority?: string;
        search?: string;
        workspace_id?: number;
      } = {};
      if (filterType === 'open') filters.status = 'open';
      if (filterType === 'urgent') filters.priority = 'Urgent';
      if (selectedCategory !== 'all') filters.category = selectedCategory;
      if (searchTerm.trim()) filters.search = searchTerm.trim();
      if (currentWorkspaceId) filters.workspace_id = currentWorkspaceId;

      const fresh = await getTickets(Object.keys(filters).length > 0 ? filters : undefined, onToast);
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
    } catch (err: any) {
      onToast(err?.detail || err?.message || `Không thể gửi phản hồi cho #${selectedTicket.id}.`, 'warning');
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
      <div className="w-full md:w-5/12 lg:w-4/12 border-r border-slate-200 bg-white flex flex-col h-1/2 md:h-full overflow-hidden shrink-0">
        <TicketToolbar
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          filterType={filterType}
          setFilterType={setFilterType}
          ticketCount={filteredTickets.length}
          demoState={demoState}
          isRefreshing={isRefreshing}
          onRefresh={handleRefreshTickets}
        />

        <TicketList
          tickets={filteredTickets}
          selectedTicket={selectedTicket}
          onSelectTicket={setSelectedTicket}
          demoState={demoState}
          onRetry={async () => {
            setDemoState('success');
            await handleRefreshTickets();
          }}
        />
      </div>

      {/* CỘT PHẢI: CHI TIẾT TICKET & AI SUGGESTED DRAFT REPLY */}
      <div className="flex-1 bg-slate-50/50 flex flex-col h-full overflow-y-auto custom-scrollbar p-4 sm:p-6">
        <TicketDetail
          selectedTicket={selectedTicket}
          demoState={demoState}
          agentReplyText={agentReplyText}
          setAgentReplyText={setAgentReplyText}
          isRegeneratingDraft={isRegeneratingDraft}
          agentSending={agentSending}
          onRegenerateDraft={handleRegenerateDraft}
          onStatusChange={handleStatusChange}
          onSendReply={handleSendAgentReply}
          onResetOriginalDraft={() => {
            if (selectedTicket) {
              setAgentReplyText(selectedTicket.draftReply);
              onToast('Đã khôi phục câu trả lời mẫu từ AI');
            }
          }}
        />
      </div>
    </div>
  );
};
