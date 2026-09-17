import React, { useState } from 'react';
import {
  Zap,
  MessageSquare,
  FileText,
  Inbox,
  Check,
  Menu,
  X,
  Activity,
  Clock,
  FolderX,
  AlertCircle
} from 'lucide-react';
import { TabType, UIState, ToastType } from '../types';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  openTicketsCount: number;
  demoState: UIState;
  setDemoState: (state: UIState) => void;
  onToast: (msg: string, type?: ToastType) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  openTicketsCount,
  demoState,
  setDemoState,
  onToast,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="shrink-0 z-30">
      {/* TOP PERSISTENT NAVBAR */}
      <header id="main-header" className="bg-white border-b border-slate-200 px-4 sm:px-6 py-2.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-indigo-400 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-100">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-slate-900 tracking-tight text-base sm:text-lg">SmartDesk AI</h1>
              <span className="bg-indigo-50 text-indigo-700 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-indigo-200/70 hidden sm:inline-block">
                Enterprise Edition
              </span>
            </div>
            <p className="text-[11px] text-slate-500 hidden sm:block">Customer Support &amp; Knowledge Automation Platform</p>
          </div>
        </div>

        {/* Navigation Tabs for 3 Screens */}
        <nav id="desktop-nav" className="hidden md:flex items-center gap-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200">
          <button
            id="tab-btn-chat"
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${activeTab === 'chat'
              ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
          >
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            1. Customer AI Chatbot
          </button>

          <button
            id="tab-btn-ticket"
            onClick={() => setActiveTab('ticket')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${activeTab === 'ticket'
              ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
          >
            <FileText className="w-4 h-4 text-indigo-600" />
            2. Submit Ticket (Form)
          </button>

          <button
            id="tab-btn-agent"
            onClick={() => setActiveTab('agent')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${activeTab === 'agent'
              ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
          >
            <Inbox className="w-4 h-4 text-indigo-600" />
            3. Agent Triage Dashboard
            <span className="bg-indigo-100 text-indigo-700 text-[10px] px-1.5 py-0.2 rounded-full font-bold ml-0.5">
              {openTicketsCount}
            </span>
          </button>
        </nav>

        {/* Mobile Hamburger */}
        <div className="flex md:hidden items-center gap-2">
          <button
            id="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200"
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Right Status Indicator */}
        <div className="hidden lg:flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200/70 px-2.5 py-1 rounded-full font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            RAG Engine: Active
          </div>
          <div className="h-4 w-px bg-slate-200"></div>
          <div className="flex items-center gap-2 text-slate-600">
            <span className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs">
              AD
            </span>
            <span className="font-semibold text-slate-700">Support Operations</span>
          </div>
        </div>
      </header>

      {/* MOBILE EXPANDED MENU */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 flex flex-col gap-2 shadow-lg z-40">
          <button
            onClick={() => { setActiveTab('chat'); setMobileMenuOpen(false); }}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${activeTab === 'chat' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
              }`}
          >
            <MessageSquare className="w-4 h-4" />
            1. Customer AI Chatbot (Hỏi đáp RAG)
          </button>
          <button
            onClick={() => { setActiveTab('ticket'); setMobileMenuOpen(false); }}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${activeTab === 'ticket' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
              }`}
          >
            <FileText className="w-4 h-4" />
            2. Submit Ticket (Form kiểm tra RFC)
          </button>
          <button
            onClick={() => { setActiveTab('agent'); setMobileMenuOpen(false); }}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${activeTab === 'agent' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
              }`}
          >
            <Inbox className="w-4 h-4" />
            3. Agent Triage Dashboard (Quản trị viên)
          </button>
        </div>
      )}

      {/* SYSTEM STATES PREVIEW BAR */}
      <div
        id="system-states-bar"
        className="bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 text-white px-4 py-2 flex flex-wrap items-center justify-between text-xs gap-2 shrink-0 border-b border-slate-800"
      >
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-5 h-5 rounded bg-indigo-500/30 text-indigo-300 font-mono font-bold text-[10px] border border-indigo-400/40">
            <Check className="w-3 h-3" />
          </span>
          <span className="font-medium text-slate-300">
            <strong className="text-white">Mô phỏng Trạng thái Hệ thống (System States):</strong>
          </span>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
          <button
            id="state-btn-success"
            onClick={() => {
              setDemoState('success');
              onToast('Đã chuyển sang SUCCESS State: Dữ liệu tải đầy đủ', 'success');
            }}
            className={`px-2.5 py-1 rounded-md font-medium text-xs transition-all flex items-center gap-1.5 ${demoState === 'success'
              ? 'bg-emerald-600 text-white shadow-xs font-bold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-300"></span>
            1. Success State
          </button>

          <button
            id="state-btn-loading"
            onClick={() => {
              setDemoState('loading');
              onToast('Đã chuyển sang LOADING State: Đang hiển thị Skeleton Loaders', 'loading');
            }}
            className={`px-2.5 py-1 rounded-md font-medium text-xs transition-all flex items-center gap-1.5 ${demoState === 'loading'
              ? 'bg-amber-600 text-white shadow-xs font-bold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-300 animate-ping"></span>
            2. Loading State
          </button>

          <button
            id="state-btn-empty"
            onClick={() => {
              setDemoState('empty');
              onToast('Đã chuyển sang EMPTY State: Hàng đợi rỗng', 'empty');
            }}
            className={`px-2.5 py-1 rounded-md font-medium text-xs transition-all flex items-center gap-1.5 ${demoState === 'empty'
              ? 'bg-blue-600 text-white shadow-xs font-bold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-300"></span>
            3. Empty State
          </button>

          <button
            id="state-btn-error"
            onClick={() => {
              setDemoState('error');
              onToast('Đã chuyển sang ERROR State: Lỗi kết nối mạng 503', 'error');
            }}
            className={`px-2.5 py-1 rounded-md font-medium text-xs transition-all flex items-center gap-1.5 ${demoState === 'error'
              ? 'bg-red-600 text-white shadow-xs font-bold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-300"></span>
            4. Error State
          </button>
        </div>
      </div>
    </div>
  );
};
