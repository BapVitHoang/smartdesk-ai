import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  Cpu,
  Clock,
  UserCheck,
  FileSearch,
  MessageSquare,
} from 'lucide-react';
import { VerificationReport, AgentTraceStep } from '../../types';

interface VerificationTraceProps {
  report: VerificationReport | null;
}

export const VerificationTrace: React.FC<VerificationTraceProps> = ({ report }) => {
  if (!report) return null;

  const scorePct = Math.round(report.faithfulness_score * 100);
  const isPassed = report.status === 'passed';
  const isWarning = report.status === 'warning';

  const traces: AgentTraceStep[] = report.agent_trace ?? [];

  const getAgentIcon = (agentName: string) => {
    const name = agentName.toLowerCase();
    if (name.includes('synthetic') || name.includes('qa')) {
      return <FileSearch className="w-4 h-4 text-indigo-600" />;
    }
    if (name.includes('sandbox') || name.includes('rag')) {
      return <UserCheck className="w-4 h-4 text-violet-600" />;
    }
    return <MessageSquare className="w-4 h-4 text-emerald-600" />;
  };

  return (
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800 text-xs sm:text-sm">
              Nhật ký sát hạch của 3 tác tử AI
            </h4>
            <p className="text-[11px] text-slate-500">
              Kết quả chỉ áp dụng cho bộ câu hỏi đã kiểm tra; vẫn nên đọc lại tài liệu trước khi xuất bản.
            </p>
          </div>
        </div>

        <span
          className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
            isPassed
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : isWarning
              ? 'bg-amber-50 text-amber-800 border-amber-200'
              : 'bg-rose-50 text-rose-800 border-rose-200'
          }`}
        >
          Độ trung thực {scorePct}% ({isPassed ? 'Đạt' : isWarning ? 'Cần xem lại' : 'Không đạt'})
        </span>
      </div>

      {traces.length === 0 && (
        <p className="text-xs text-slate-500">
          Chưa có nhật ký sát hạch cho tài liệu này. Bấm “Sát hạch AI” để chạy lại quy trình 3 tác tử.
        </p>
      )}

      {/* 3-Agent Trace Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {traces.map((step, idx) => {
          const isSuccess = step.status === 'success';
          const isFailed = step.status === 'failed';

          return (
            <div
              key={idx}
              className="p-3.5 bg-white border border-slate-200 rounded-xl space-y-2 shadow-2xs hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  {getAgentIcon(step.agent)}
                  <span className="font-bold text-xs text-slate-900">{step.agent}</span>
                </div>
                {isSuccess ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    Đạt
                  </span>
                ) : isFailed ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                    <XCircle className="w-3 h-3 text-rose-600" />
                    Không đạt
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    <AlertTriangle className="w-3 h-3 text-amber-500" />
                    Cần xem lại
                  </span>
                )}
              </div>

              <p className="text-[11px] text-slate-600 leading-relaxed font-normal">
                {step.action}
              </p>

              {step.output_summary && (
                <div className="p-2 bg-slate-50 border border-slate-100 rounded-lg text-[10px] text-slate-700">
                  <span className="font-bold text-slate-900 block mb-0.5">Kết luận thẩm định:</span>
                  <span>{step.output_summary}</span>
                </div>
              )}

              {step.latency_ms !== undefined && (
                <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono pt-1">
                  <Clock className="w-3 h-3" />
                  <span>Độ trễ: {step.latency_ms}ms</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
