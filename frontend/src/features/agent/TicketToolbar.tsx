import React from 'react';
import { Search, X, Filter, RefreshCw, ArrowUpDown } from 'lucide-react';
import { UIState } from '../../types';

export type TicketSortField = 'created_at' | 'priority' | 'status' | 'sla_hours';

interface TicketToolbarProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  selectedCategory: string;
  setSelectedCategory: (cat: string) => void;
  filterType: 'all' | 'open' | 'urgent';
  setFilterType: (ft: 'all' | 'open' | 'urgent') => void;
  sortBy?: TicketSortField;
  setSortBy?: (sort: TicketSortField) => void;
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
  sortBy = 'created_at',
  setSortBy,
  ticketCount,
  demoState,
  isRefreshing,
  onRefresh,
}) => {
  return (
    <>
      {/* Header bar */}
      <div className="px-3 py-2 border-b border-slate-300 bg-slate-100 flex items-center justify-between shrink-0">
        <h2 className="font-bold text-slate-900 text-xs sm:text-sm">Hàng đợi yêu cầu hỗ trợ</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Làm mới hàng đợi từ máy chủ"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 border border-slate-200 bg-white transition-all shadow-xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
            {demoState === 'empty' ? 0 : ticketCount} yêu cầu
          </span>
        </div>
      </div>

      {/* Search, Category Filter & Sorting Dropdown */}
      <div className="px-3 py-2 bg-white border-b border-slate-200 space-y-1.5 shrink-0">
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
          <input
            id="agent-ticket-search-input"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm theo mã ticket (#TICK), tên, tiêu đề..."
            className="w-full pl-8 pr-7 py-1 text-[11px] bg-slate-100 border border-slate-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 focus:bg-white transition-all text-slate-900 placeholder:text-slate-500"
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

        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-0.5" />
            <select
              id="agent-ticket-category-select"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full text-[10px] py-1 px-2 bg-slate-100 border border-slate-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 focus:bg-white text-slate-900 font-medium cursor-pointer transition-colors"
            >
              <option value="all">Tất cả danh mục</option>
              <option value="Authentication">Authentication</option>
              <option value="Billing">Billing</option>
              <option value="Bug Report">Bug Report</option>
              <option value="Feature Request">Feature Request</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-0.5" />
            <select
              id="agent-ticket-sort-select"
              value={sortBy}
              onChange={(e) => setSortBy && setSortBy(e.target.value as TicketSortField)}
              className="w-full text-[10px] py-1 px-2 bg-slate-100 border border-slate-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 focus:bg-white text-slate-900 font-medium cursor-pointer transition-colors"
            >
              <option value="created_at">Mới nhất (Date)</option>
              <option value="priority">Mức ưu tiên (Priority)</option>
              <option value="status">Trạng thái (Status)</option>
              <option value="sla_hours">Cam kết SLA (SLA Hours)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Filter Quick Tabs (Status / Urgency) */}
      <div className="px-2.5 py-1.5 bg-slate-100 border-b border-slate-300 flex items-center gap-1.5 shrink-0 text-[11px]">
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
