import React, { useState } from 'react';
import {
  Zap,
  MessageSquare,
  FileText,
  Inbox,
  Menu,
  X,
  BookOpen,
  Lock,
} from 'lucide-react';
import { TabType, ToastType, User as UserType } from '../types';
import { LoginSwitcher } from '../features/auth';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  openTicketsCount: number;
  onToast: (msg: string, type?: ToastType) => void;
  currentUser?: UserType | null;
  onUserChanged?: (user: UserType | null) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  openTicketsCount,
  onToast,
  currentUser,
  onUserChanged,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isAdmin = currentUser?.role === 'admin';

  return (
    <div className="shrink-0 z-30">
      {/* TOP PERSISTENT NAVBAR */}
      <header
        id="main-header"
        className="bg-white border-b border-slate-200 px-4 sm:px-6 py-2.5 flex items-center justify-between shadow-xs"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-indigo-400 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-100">
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900 tracking-tight text-base sm:text-lg">
              SmartDesk AI
            </h1>
          </div>
        </div>

        {/* Navigation Tabs for Screens */}
        <nav
          id="desktop-nav"
          className="hidden md:flex items-center gap-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200"
        >
          <button
            id="tab-btn-chat"
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'chat'
                ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            <MessageSquare className="w-4 h-4 text-indigo-600" />
            1. Hỏi trợ lý AI
          </button>

          <button
            id="tab-btn-ticket"
            onClick={() => setActiveTab('ticket')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'ticket'
                ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            <FileText className="w-4 h-4 text-indigo-600" />
            2. Gửi yêu cầu hỗ trợ
          </button>

          {/* Tab 3: Agent Triage Dashboard (Admin only) */}
          {isAdmin ? (
            <button
              id="tab-btn-agent"
              onClick={() => setActiveTab('agent')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'agent'
                  ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
            >
              <Inbox className="w-4 h-4 text-indigo-600" />
              3. Điều phối yêu cầu
              <span className="bg-indigo-100 text-indigo-700 text-[10px] px-1.5 py-0.2 rounded-full font-bold ml-0.5">
                {openTicketsCount}
              </span>
            </button>
          ) : (
            <div
              title="Chỉ Quản trị viên mới mở được trang Điều phối yêu cầu"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 opacity-60 cursor-not-allowed select-none"
            >
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span>3. Điều phối yêu cầu</span>
              <span className="text-[10px] bg-slate-200 text-slate-600 px-1.5 py-0.2 rounded font-bold">Quản trị</span>
            </div>
          )}

          {/* Tab 4: Knowledge Base (Admin only) */}
          {isAdmin ? (
            <button
              id="tab-btn-knowledge"
              onClick={() => setActiveTab('knowledge')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'knowledge'
                  ? 'bg-white text-indigo-700 shadow-xs border border-slate-200/60'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }`}
            >
              <BookOpen className="w-4 h-4 text-indigo-600" />
              4. Quản lý Tri thức &amp; Sát hạch
            </button>
          ) : (
            <div
              title="Chỉ Quản trị viên mới mở được trang Quản lý tri thức"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 opacity-60 cursor-not-allowed select-none"
            >
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span>4. Tri thức &amp; Sát hạch</span>
              <span className="text-[10px] bg-slate-200 text-slate-600 px-1.5 py-0.2 rounded font-bold">Quản trị</span>
            </div>
          )}
        </nav>

        {/* Right Section: RAG status & LoginSwitcher */}
        <div className="flex items-center gap-3">
          <div className="hidden xl:flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200/70 px-2.5 py-1 rounded-full text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            RAG Engine: Active
          </div>

          {/* Login / Role Switcher Component */}
          <LoginSwitcher
            currentUser={currentUser}
            onUserChanged={onUserChanged}
            onToast={onToast}
          />

          {/* Mobile Hamburger */}
          <div className="flex md:hidden items-center ml-1">
            <button
              id="mobile-menu-toggle"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer"
              aria-label={mobileMenuOpen ? 'Đóng menu' : 'Mở menu'}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* MOBILE EXPANDED MENU */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 flex flex-col gap-2 shadow-lg z-40">
          <button
            onClick={() => {
              setActiveTab('chat');
              setMobileMenuOpen(false);
            }}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${
              activeTab === 'chat' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            1. Hỏi trợ lý AI
          </button>
          <button
            onClick={() => {
              setActiveTab('ticket');
              setMobileMenuOpen(false);
            }}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${
              activeTab === 'ticket' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
            }`}
          >
            <FileText className="w-4 h-4" />
            2. Gửi yêu cầu hỗ trợ
          </button>
          {isAdmin && (
            <>
              <button
                onClick={() => {
                  setActiveTab('agent');
                  setMobileMenuOpen(false);
                }}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${
                  activeTab === 'agent' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
                }`}
              >
                <Inbox className="w-4 h-4" />
                3. Điều phối yêu cầu
              </button>
              <button
                onClick={() => {
                  setActiveTab('knowledge');
                  setMobileMenuOpen(false);
                }}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold text-left ${
                  activeTab === 'knowledge' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'
                }`}
              >
                <BookOpen className="w-4 h-4" />
                4. Quản lý Tri thức &amp; Sát hạch
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
};
