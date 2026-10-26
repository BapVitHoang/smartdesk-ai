import React, { useState, useEffect } from 'react';
import {
  Activity,
  DollarSign,
  Cpu,
  Clock,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Zap,
  Terminal,
  Unlock,
} from 'lucide-react';
import { ToastType } from '../../types';
import {
  getAiUsageSummary,
  resetAiCooldown,
  ExtendedAIUsageStats,
} from '../../services/api';

interface TelemetryPanelProps {
  onToast?: (msg: string, type?: ToastType) => void;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ onToast }) => {
  const [stats, setStats] = useState<ExtendedAIUsageStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [resettingCooldown, setResettingCooldown] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await getAiUsageSummary();
      setStats(data);
    } catch {
      if (onToast) onToast('Không thể tải dữ liệu telemetry, sử dụng dữ liệu cục bộ.', 'warning');
    } finally {
      setLoading(false);
    }
  };

  const handleResetCooldown = async () => {
    setResettingCooldown(true);
    try {
      const res = await resetAiCooldown();
      if (onToast) {
        onToast(res.message || 'Đã mở khóa Cooldown Circuit Breaker thành công!', 'success');
      }
      await fetchStats();
    } catch (err: any) {
      if (onToast) {
        onToast(err?.detail || err?.message || 'Không thể mở khóa cooldown.', 'error');
      }
    } finally {
      setResettingCooldown(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const formatTimeAgo = (dateStr?: string) => {
    if (!dateStr) return 'vừa xong';
    try {
      const date = new Date(dateStr);
      const diffMs = Date.now() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 60) return `${diffSec}s trước`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m trước`;
      const diffHours = Math.floor(diffMin / 60);
      return `${diffHours}h trước`;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-white border border-slate-200 rounded-2xl shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Giám Sát AI &amp; Bảo Vệ Chi Phí (AI Telemetry &amp; Cost-Guard)
            </h2>
            <p className="text-xs text-slate-500">
              Theo dõi thời gian thực lượt gọi LLM, token, chi phí USD, độ trễ và trạng thái Circuit Breaker
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchStats}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors cursor-pointer"
            title="Làm mới thống kê"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-600' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>
      </div>

      {/* 2. Circuit Breaker Cooldown Alert Banner */}
      {stats?.cooldown_active ? (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-700 shrink-0">
              <AlertTriangle className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-amber-900">
                  Cost-Guard Circuit Breaker Đang Kích Hoạt
                </span>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-amber-200 text-amber-800 rounded-full">
                  HTTP 429 Cooldown
                </span>
              </div>
              <p className="text-xs text-amber-700 mt-0.5">
                Google Gemini API đã chạm giới hạn Rate Limit. Hệ thống đang tự động điều hướng truy vấn sang bộ tìm kiếm tất định BM25 để tránh gián đoạn dịch vụ.
              </p>
            </div>
          </div>
          <button
            onClick={handleResetCooldown}
            disabled={resettingCooldown}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 active:bg-amber-800 rounded-xl shadow-xs transition-colors cursor-pointer shrink-0"
          >
            <Unlock className="w-3.5 h-3.5" />
            <span>{resettingCooldown ? 'Đang mở khóa...' : 'Mở Khóa Cooldown 429'}</span>
          </button>
        </div>
      ) : (
        <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-2xl flex items-center justify-between gap-3 text-xs text-emerald-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Cost-Guard Circuit Breaker Sẵn Sàng:</strong> Không có khóa Rate Limit (HTTP 429) nào đang kích hoạt. Cloud Gemini hoạt động bình thường.
            </span>
          </div>
          <button
            onClick={handleResetCooldown}
            disabled={resettingCooldown}
            className="px-2.5 py-1 text-[11px] font-medium text-emerald-700 hover:text-emerald-900 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer shrink-0"
            title="Kiểm tra mở lại circuit breaker thủ công"
          >
            Đặt lại Cooldown
          </button>
        </div>
      )}

      {/* 3. Four Core KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Total Requests */}
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Tổng Lượt Yêu Cầu AI</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_requests ?? 0}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="text-emerald-600 font-semibold">{stats?.success_count ?? 0} thành công</span>
            <span>•</span>
            <span className="text-slate-400">{stats?.error_count ?? 0} lỗi</span>
          </div>
        </div>

        {/* KPI 2: Total Tokens & Cost */}
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Chi Phí &amp; Token</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            ${stats?.total_cost_usd !== undefined ? stats.total_cost_usd.toFixed(4) : '0.0000'}
          </div>
          <div className="text-[11px] text-slate-500">
            Trung bình <strong>${(stats?.avg_cost_usd ?? (stats?.total_requests ? (stats.total_cost_usd ?? 0) / stats.total_requests : 0)).toFixed(6)}</strong>/yêu cầu
          </div>
          <div className="text-[11px] text-slate-500">
            Tổng <strong>{(stats?.total_tokens ?? 0).toLocaleString()}</strong> tokens
            {stats?.total_input_tokens ? ` (${stats.total_input_tokens.toLocaleString()} in / ${stats.total_output_tokens?.toLocaleString()} out)` : ''}
          </div>
        </div>

        {/* KPI 3: Average Latency */}
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Độ Trễ Trung Bình</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.avg_latency_ms ?? 0} <span className="text-sm font-normal text-slate-500">ms</span>
          </div>
          <div className="text-[11px] text-slate-500">
            Mục tiêu SLA: <span className="text-indigo-600 font-semibold">&lt; 1,500ms</span>
          </div>
        </div>

        {/* KPI 4: Fallback & Refusal Count */}
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium">Dự Phòng / Từ Chối</span>
            <div className="w-7 h-7 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-violet-600">
            {stats?.fallback_count ?? 0}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span>BM25 FAQ fallback</span>
            {stats?.refused_count ? (
              <>
                <span>•</span>
                <span className="text-rose-500 font-medium">{stats.refused_count} guardrail</span>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {/* 4. Model Distribution Breakdown */}
      {stats?.model_breakdown && Object.keys(stats.model_breakdown).length > 0 && (
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Phân Bổ Lượt Gọi Theo Mô Hình AI
          </h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.model_breakdown).map(([model, count]) => {
              const isCloud = model.includes('gemini');
              const isFallback = model.includes('bm25') || model.includes('seed');
              const badgeBg = isCloud
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                : isFallback
                ? 'bg-amber-50 border-amber-200 text-amber-700'
                : 'bg-slate-100 border-slate-200 text-slate-700';

              return (
                <div
                  key={model}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium ${badgeBg}`}
                >
                  <span>{model}</span>
                  <span className="px-1.5 py-0.5 rounded-md bg-white font-bold text-[11px] shadow-2xs">
                    {count} reqs
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Recent AI Telemetry Logs Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-indigo-600" />
            <h3 className="font-bold text-sm text-slate-900">
              Nhật Ký Gọi AI Gần Đây (Audit &amp; Telemetry Logs)
            </h3>
          </div>
          <span className="text-xs text-slate-500">
            {stats?.recent_logs?.length ?? 0} bản ghi gần nhất
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Thời Gian</th>
                <th className="py-3 px-4">Điểm Cuối</th>
                <th className="py-3 px-4">Mô Hình / Provider</th>
                <th className="py-3 px-4">Công Cụ (Tools)</th>
                <th className="py-3 px-4 text-right">Tokens</th>
                <th className="py-3 px-4 text-right">Độ Trễ</th>
                <th className="py-3 px-4 text-right">Chi Phí</th>
                <th className="py-3 px-4 text-center">Trạng Thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {!stats?.recent_logs || stats.recent_logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Chưa có nhật ký gọi AI nào được ghi nhận.
                  </td>
                </tr>
              ) : (
                stats.recent_logs.map((log: any) => {
                  const isSuccess = log.status === 'success';
                  const isFallback = log.status === 'fallback';
                  const isRefused = log.status === 'refused';

                  return (
                    <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                        {formatTimeAgo(log.created_at)}
                      </td>
                      <td className="py-3 px-4 font-mono text-indigo-600 font-medium">
                        {log.endpoint || '/api/v1/chat'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-slate-800">{log.model_name}</span>
                          {log.prompt_version && (
                            <span className="px-1.5 py-0.2 bg-slate-100 text-slate-500 rounded text-[10px]">
                              {log.prompt_version}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {log.tools_called && log.tools_called.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {log.tools_called.map((tool: string, i: number) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 bg-violet-50 text-violet-700 border border-violet-200 rounded text-[10px] font-medium"
                              >
                                {tool}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-[11px]">
                        {(log.total_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-[11px]">
                        {log.latency_ms || 0}ms
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-[11px] text-emerald-600 font-medium">
                        ${log.cost_usd !== undefined ? Number(log.cost_usd).toFixed(5) : '0.00000'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {isSuccess && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" />
                            Success
                          </span>
                        )}
                        {isFallback && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            <Zap className="w-3 h-3" />
                            Fallback
                          </span>
                        )}
                        {isRefused && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                            <XCircle className="w-3 h-3" />
                            Refused
                          </span>
                        )}
                        {!isSuccess && !isFallback && !isRefused && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                            {log.status}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
