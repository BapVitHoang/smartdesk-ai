import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ChatView } from './components/ChatView';
import { TicketFormView } from './components/TicketFormView';
import { AgentDashboardView } from './components/AgentDashboardView';
import { KnowledgeManagerView } from './components/KnowledgeManagerView';
import { Footer } from './components/Footer';
import {
  TabType,
  UIState,
  Ticket,
  ChatMessage,
  Toast,
  ToastType,
  TicketStatus,
  TicketFormData,
  User,
} from './types';
import { INITIAL_TICKETS, INITIAL_CHAT_MESSAGES } from './data';
import { registerApiToastHandler, getTickets, getCurrentUser } from './services/api';
import { CheckCircle2, AlertCircle, Info, X, Loader2, Inbox } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<number>(1);
  const [tickets, setTickets] = useState<Ticket[]>(INITIAL_TICKETS);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(INITIAL_TICKETS[0]);
  const [demoState, setDemoState] = useState<UIState>('success');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES);
  const [prefillTicketData, setPrefillTicketData] = useState<Partial<TicketFormData> | undefined>(undefined);
  const [toast, setToast] = useState<Toast | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const showToast = (message: string, type: ToastType = 'success') => {
    const newToast: Toast = {
      id: String(Date.now()),
      message,
      type,
    };
    setToast(newToast);
    setTimeout(() => {
      setToast((current) => (current?.id === newToast.id ? null : current));
    }, 4000);
  };

  useEffect(() => {
    // 1. Register global toast notifier for API fallbacks
    registerApiToastHandler(showToast);

    // 2. Fetch current logged-in user profile
    getCurrentUser().then((user) => {
      if (user) {
        setCurrentUser(user);
      }
    });

    // 3. Fetch real-time tickets from FastAPI backend for the current workspace (limit: 50 for full seed)
    const loadTicketsForWorkspace = async () => {
      try {
        const remoteTickets = await getTickets({ workspace_id: currentWorkspaceId, limit: 50 }, showToast);
        if (remoteTickets && remoteTickets.length > 0) {
          setTickets(remoteTickets);
          setSelectedTicket(remoteTickets[0]);
        }
      } catch (err) {
        console.warn('Backend unavailable, using initial sample data:', err);
      }
    };

    loadTicketsForWorkspace();

    return () => {
      registerApiToastHandler(null);
    };
  }, [currentWorkspaceId]);

  const handleUserChanged = (newUser: User | null) => {
    setCurrentUser(newUser);

    // Refresh tickets list for new user context (RBAC isolation: admin gets all 43, user gets isolated tickets)
    getTickets({ workspace_id: currentWorkspaceId, limit: 50 }, showToast)
      .then((remoteTickets) => {
        if (remoteTickets && remoteTickets.length > 0) {
          setTickets(remoteTickets);
          setSelectedTicket(remoteTickets[0]);
        }
      })
      .catch((err) => console.warn('Failed to refresh tickets on user change:', err));

    // RBAC: If switching to normal user, immediately navigate away from admin-only tabs
    if (newUser && newUser.role === 'user' && (activeTab === 'agent' || activeTab === 'knowledge')) {
      setActiveTab('chat');
      showToast('Đã chuyển hướng về Chat Bot do vai trò Khách hàng không có quyền truy cập tab Quản trị.', 'info');
    }
  };

  const handleEscalateToTicket = (prefill?: Partial<TicketFormData>) => {
    setPrefillTicketData(prefill);
    setActiveTab('ticket');
  };

  const handleTicketCreated = (newTicket: Ticket) => {
    setTickets((prev) => [newTicket, ...prev]);
    setSelectedTicket(newTicket);
    setPrefillTicketData(undefined);
  };

  const handleUpdateTicketStatus = (ticketId: string, newStatus: TicketStatus, draftReply?: string) => {
    setTickets((prev) =>
      prev.map((t) =>
        t.id === ticketId
          ? { ...t, status: newStatus, draftReply: draftReply !== undefined ? draftReply : t.draftReply }
          : t
      )
    );
    setSelectedTicket((prev) =>
      prev && prev.id === ticketId
        ? { ...prev, status: newStatus, draftReply: draftReply !== undefined ? draftReply : prev.draftReply }
        : prev
    );
  };

  const openTicketsCount = tickets.filter((t) => t.status === 'Open').length;

  const getToastBgColor = (type: ToastType) => {
    switch (type) {
      case 'error':
        return '#e11d48'; // Red-600
      case 'loading':
      case 'warning':
        return '#d97706'; // Amber-600
      case 'empty':
        return '#2563eb'; // Blue-600
      case 'info':
        return '#0284c7'; // Sky-600
      case 'success':
      default:
        return '#059669'; // Emerald-600
    }
  };

  const renderToastIcon = (type: ToastType) => {
    switch (type) {
      case 'error':
        return <AlertCircle className="w-5 h-5 text-white shrink-0" />;
      case 'loading':
      case 'warning':
        return <Loader2 className="w-5 h-5 text-white shrink-0 animate-spin" />;
      case 'empty':
        return <Inbox className="w-5 h-5 text-white shrink-0" />;
      case 'info':
        return <Info className="w-5 h-5 text-white shrink-0" />;
      case 'success':
      default:
        return <CheckCircle2 className="w-5 h-5 text-white shrink-0" />;
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-200 text-slate-800 antialiased selection:bg-indigo-500 selection:text-white">
      {/* Toast Notification Container */}
      {toast && (
        <div
          id="global-toast"
          role="alert"
          className="fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-white font-medium text-sm transition-all duration-300"
          style={{
            backgroundColor: getToastBgColor(toast.type),
          }}
        >
          {renderToastIcon(toast.type)}
          <span>{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            className="ml-2 hover:opacity-75 focus:outline-none cursor-pointer"
            aria-label="Đóng thông báo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        openTicketsCount={openTicketsCount}
        onToast={showToast}
        currentUser={currentUser}
        onUserChanged={handleUserChanged}
      />

      {/* Main Screen Viewport */}
      <main className="flex-1 overflow-hidden flex flex-col bg-slate-200">
        {activeTab === 'chat' && (
          <ChatView
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            setActiveTab={setActiveTab}
            onEscalateToTicket={handleEscalateToTicket}
            onToast={showToast}
            currentWorkspaceId={currentWorkspaceId}
            setCurrentWorkspaceId={setCurrentWorkspaceId}
            demoState={demoState}
          />
        )}

        {activeTab === 'ticket' && (
          <TicketFormView
            onTicketCreated={handleTicketCreated}
            setActiveTab={setActiveTab}
            setSelectedTicket={setSelectedTicket}
            initialData={prefillTicketData}
            onToast={showToast}
            currentWorkspaceId={currentWorkspaceId}
            demoState={demoState}
          />
        )}

        {activeTab === 'agent' && currentUser?.role === 'admin' && (
          <AgentDashboardView
            tickets={tickets}
            setTickets={setTickets}
            selectedTicket={selectedTicket}
            setSelectedTicket={setSelectedTicket}
            demoState={demoState}
            setDemoState={setDemoState}
            onUpdateTicketStatus={handleUpdateTicketStatus}
            onToast={showToast}
            currentWorkspaceId={currentWorkspaceId}
          />
        )}

        {activeTab === 'knowledge' && currentUser?.role === 'admin' && (
          <KnowledgeManagerView
            currentWorkspaceId={currentWorkspaceId}
            setCurrentWorkspaceId={setCurrentWorkspaceId}
            demoState={demoState}
            onToast={showToast}
          />
        )}
      </main>

      {/* Footer Metadata */}
      <Footer />
    </div>
  );
}
