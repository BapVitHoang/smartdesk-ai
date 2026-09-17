import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ChatView } from './components/ChatView';
import { TicketFormView } from './components/TicketFormView';
import { AgentDashboardView } from './components/AgentDashboardView';
import { Footer } from './components/Footer';
import { TabType, UIState, Ticket, ChatMessage, Toast, ToastType, TicketStatus } from './types';
import { INITIAL_TICKETS, INITIAL_CHAT_MESSAGES } from './data';
import { registerApiToastHandler, getTickets } from './services/api';
import { CheckCircle2, AlertCircle, Info, X, Loader2, Inbox } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [tickets, setTickets] = useState<Ticket[]>(INITIAL_TICKETS);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(INITIAL_TICKETS[0]);
  const [demoState, setDemoState] = useState<UIState>('success');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES);
  const [toast, setToast] = useState<Toast | null>(null);

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

    // 2. Fetch real-time tickets from FastAPI backend
    const loadInitialTickets = async () => {
      try {
        const remoteTickets = await getTickets(undefined, showToast);
        if (remoteTickets && remoteTickets.length > 0) {
          setTickets(remoteTickets);
          setSelectedTicket(remoteTickets[0]);
        }
      } catch (err) {
        console.warn('Backend unavailable, using initial sample data:', err);
      }
    };

    loadInitialTickets();

    return () => {
      registerApiToastHandler(null);
    };
  }, []);

  const handleTicketCreated = (newTicket: Ticket) => {
    setTickets((prev) => [newTicket, ...prev]);
    setSelectedTicket(newTicket);
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
        return '#d97706'; // Amber-600 (distinct for Loading State)
      case 'empty':
        return '#2563eb'; // Blue-600 (distinct for Empty State)
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
    <div className="flex flex-col h-screen overflow-hidden bg-slate-100 text-slate-800 antialiased selection:bg-indigo-500 selection:text-white">
      
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
            className="ml-2 hover:opacity-75 focus:outline-none"
            aria-label="Đóng thông báo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header & System States Bar */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        openTicketsCount={openTicketsCount}
        demoState={demoState}
        setDemoState={setDemoState}
        onToast={showToast}
      />

      {/* Main Screen Viewport */}
      <main className="flex-1 overflow-hidden flex flex-col bg-slate-100">
        {activeTab === 'chat' && (
          <ChatView
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            setActiveTab={setActiveTab}
            onToast={showToast}
          />
        )}

        {activeTab === 'ticket' && (
          <TicketFormView
            onTicketCreated={handleTicketCreated}
            setActiveTab={setActiveTab}
            setSelectedTicket={setSelectedTicket}
            onToast={showToast}
          />
        )}

        {activeTab === 'agent' && (
          <AgentDashboardView
            tickets={tickets}
            setTickets={setTickets}
            selectedTicket={selectedTicket}
            setSelectedTicket={setSelectedTicket}
            demoState={demoState}
            setDemoState={setDemoState}
            onUpdateTicketStatus={handleUpdateTicketStatus}
            onToast={showToast}
          />
        )}
      </main>

      {/* Footer Metadata */}
      <Footer />
    </div>
  );
}
