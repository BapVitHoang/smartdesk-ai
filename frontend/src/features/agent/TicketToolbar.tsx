import React from 'react';
import { Search, X, Filter, RefreshCw } from 'lucide-react';
import { UIState } from '../../types';

interface TicketToolbarProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  selectedCategory: string;
  setSelectedCategory: (cat: string) => void;
  filterType: 'all' | 'open' | 'urgent';
  setFilterType: (ft: 'all' | 'open' | 'urgent') => void;
  ticketCount: number;
  demoState: UIState;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export const TicketToolbar: React.FC<TicketToolbarProps> = ({
  searchTerm,
  setSearchTerm,
  selectedCategory,
  setSelectedCategory,
  filterType,
  setFilterType,
  ticketCount,
  demoState,
  isRefreshing,
  onRefresh,
}) => {
  return (
    <>
      {/* Header bar */}
      <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
        <div>
          <h2 className="font-bold text-slate-900 text-sm sm:text-base">Hàng đợi Ticket (Triage Queue)</h2>
          <p className="text-xs text-slate-500">Phân loại &amp; gán nhãn tự động bởi SmartDesk</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Làm mới hàng đợi từ máy chủ"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 bg-white transition-all shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
          <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-700">
            {demoState === 'empty' ? 0 : ticketCount} tickets
          </span>
        </div>
      </div>

      {/* Search and Category Filter */}
      <div className="p-3 bg-white border-b border-slate-200 space-y-2 shrink-0">
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            id="agent-ticket-search-input"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm theo mã ticket (#TICK), tên, tiêu đề..."
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 focus:bg-white transition-all text-slate-800 placeholder:text-slate-400"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-2 p-0.5 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors cursor-pointer"
              title="Xóa tìm kiếm"
              aria-label="Xóa tìm kiếm"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
          <select
            id="agent-ticket-category-select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full text-xs py-1.5 px-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 text-slate-700 font-medium cursor-pointer transition-colors"
          >
            <option value="all">Tất cả danh mục (All Categories)</option>
            <option value="Authentication">Authentication (Đăng nhập, 2FA)</option>
            <option value="Billing">Billing (Thanh toán, Hoàn tiền)</option>
            <option value="Bug Report">Bug Report (Lỗi kỹ thuật, Timeout)</option>
            <option value="Feature Request">Feature Request (Đề xuất tính năng)</option>
          </select>
        </div>
      </div>

      {/* Filter Quick Tabs (Status / Urgency) */}
      <div className="px-3 py-2 bg-slate-50/50 border-b border-slate-100 flex items-center gap-1.5 shrink-0 text-xs">
        <button
          onClick={() => setFilterType('all')}
          className={`px-2.5 py-1 rounded-lg font-medium text-xs transition-all cursor-pointer ${
            filterType === 'all'
              ? 'bg-slate-900 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Tất cả
        </button>
        <button
          onClick={() => setFilterType('open')}
          className={`px-2.5 py-1 rounded-lg font-medium text-xs transition-all cursor-pointer ${
            filterType === 'open'
              ? 'bg-indigo-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Chưa xử lý (Open)
        </button>
        <button
          onClick={() => setFilterType('urgent')}
          className={`px-2.5 py-1 rounded-lg font-medium text-xs transition-all cursor-pointer ${
            filterType === 'urgent'
              ? 'bg-rose-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Khẩn cấp (Urgent)
        </button>
      </div>
    </>
  );
};
