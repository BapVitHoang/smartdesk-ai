import React, { useState, useEffect } from 'react';
import { Activity, DollarSign, Cpu, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import { AIUsageStats } from '../../types';
import { getAiUsageSummary } from '../../services/api';

export const TelemetryPanel: React.FC = () => {
  const [stats, setStats] = useState<AIUsageStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await getAiUsageSummary();
      setStats(data);
    } catch {
      // Local fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-600" />
          <h3 className="font-bold text-slate-900 text-sm">Giám sát &amp; Chi phí AI (Telemetry &amp; Cost-Guard)</h3>
        </div>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="p-1 text-slate-400 hover:text-indigo-600 rounded-lg transition-colors cursor-pointer"
          title="Làm mới thống kê"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
            <Cpu className="w-3 h-3 text-indigo-500" />
            <span>Tổng Yêu Cầu</span>
          </div>
          <div className="text-base font-bold text-slate-900">{stats?.total_requests ?? 0}</div>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
            <DollarSign className="w-3 h-3 text-emerald-500" />
            <span>Ước Tính Chi Phí</span>
          </div>
          <div className="text-base font-bold text-emerald-600">
            ${stats?.total_cost_usd?.toFixed(4) ?? '0.0000'}
          </div>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
            <Clock className="w-3 h-3 text-amber-500" />
            <span>Độ Trễ TB</span>
          </div>
          <div className="text-base font-bold text-slate-900">{stats?.avg_latency_ms ?? 0} ms</div>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 font-medium">
            <AlertCircle className="w-3 h-3 text-violet-500" />
            <span>Số Lần Dự Phòng</span>
          </div>
          <div className="text-base font-bold text-slate-900">{stats?.fallback_count ?? 0}</div>
        </div>
      </div>
    </div>
  );
};
