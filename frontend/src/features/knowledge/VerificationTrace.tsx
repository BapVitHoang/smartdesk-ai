import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';
import { VerificationReport } from '../../types';

interface VerificationTraceProps {
  report: VerificationReport | null;
}

export const VerificationTrace: React.FC<VerificationTraceProps> = ({ report }) => {
  if (!report) return null;

  const scorePct = Math.round(report.faithfulness_score * 100);
  const isPassed = report.status === 'passed';
  const isWarning = report.status === 'warning';

  return (
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-indigo-600" />
          <h4 className="font-bold text-slate-800 text-xs">Báo Cáo Sát Hạch Độ Trung Thực (Faithfulness Judge)</h4>
        </div>
        <span
          className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
            isPassed
              ? 'bg-emerald-100 text-emerald-800'
              : isWarning
              ? 'bg-amber-100 text-amber-800'
              : 'bg-rose-100 text-rose-800'
          }`}
        >
          {scorePct}% ({report.status.toUpperCase()})
        </span>
      </div>

      <div className="space-y-2">
        {report.items.map((item) => (
          <div key={item.id} className="p-2.5 bg-white border border-slate-100 rounded-xl text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800 line-clamp-1">{item.question}</span>
              {item.status === 'passed' ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              ) : item.status === 'warning' ? (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              )}
            </div>
            <p className="text-[11px] text-slate-500 line-clamp-2">{item.rag_answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
