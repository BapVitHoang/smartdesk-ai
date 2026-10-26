import React from 'react';
import { Inbox, AlertTriangle, RefreshCw, Tag } from 'lucide-react';
import { Ticket, UIState } from '../../types';

interface TicketListProps {
  tickets: Ticket[];
  selectedTicket: Ticket | null;
  onSelectTicket: (ticket: Ticket) => void;
  demoState: UIState;
  onRetry: () => void;
}

export const TicketList: React.FC<TicketListProps> = ({
  tickets,
  selectedTicket,
  onSelectTicket,
  demoState,
  onRetry,
}) => {
  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2.5 bg-slate-200">
      {/* 1. LOADING STATE (Skeleton Loaders) */}
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

      {/* 2. EMPTY STATE */}
      {demoState === 'empty' && (
        <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400">
            <Inbox className="w-8 h-8" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800 text-sm">Chưa có yêu cầu hỗ trợ nào phù hợp</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
              Hàng đợi đang trống hoặc không có yêu cầu khớp bộ lọc. Hãy đổi bộ lọc hoặc bấm Làm mới.
            </p>
          </div>
          <button
            onClick={onRetry}
            className="px-4 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200 transition-colors inline-flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Làm mới</span>
          </button>
        </div>
      )}

      {/* 3. ERROR STATE */}
      {demoState === 'error' && (
        <div className="p-2">
          <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-5 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-rose-900 text-sm">Không tải được danh sách yêu cầu</h4>
              <p className="text-xs text-rose-700 mt-1">
                Không kết nối được máy chủ. Kiểm tra mạng rồi bấm Thử lại. Nếu vẫn lỗi, hãy báo quản trị viên.
              </p>
            </div>
            <button
              onClick={onRetry}
              className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs transition-colors inline-flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử lại</span>
            </button>
          </div>
        </div>
      )}

      {/* 4. SUCCESS STATE (Ticket Cards) */}
      {demoState === 'success' && (
        tickets.length > 0 ? (
          tickets.map((t) => {
            const isSelected = selectedTicket?.id === t.id;
            const cardTone =
              t.status === 'Open'
                ? 'bg-sky-50 border-sky-300 hover:bg-sky-100/70'
                : t.status === 'Pending'
                ? 'bg-amber-50 border-amber-300 hover:bg-amber-100/70'
                : t.status === 'Resolved'
                ? 'bg-emerald-50 border-emerald-300 hover:bg-emerald-100/70'
                : 'bg-white border-slate-200 hover:bg-slate-50';
            return (
              <div
                key={t.id}
                onClick={() => onSelectTicket(t)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer text-left ${cardTone} ${
                  isSelected ? 'shadow-xs ring-2 ring-indigo-500' : ''
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
  );
};
