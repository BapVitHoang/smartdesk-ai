/**
 * AI Telemetry & Observability API Service (REQ-22, REQ-33)
 */

import { AIUsageStats, AIUsageLogItem, ResetCooldownResponse } from '../../types';
import {
  API_BASE_URL,
  ApiError,
  fetchWithTimeout,
  getAuthHeaders,
} from './client';

export interface TelemetryLogItem extends AIUsageLogItem {
  prompt_version?: string;
  tools_called?: string[];
}

export interface ExtendedAIUsageStats extends AIUsageStats {
  total_input_tokens?: number;
  total_output_tokens?: number;
  success_count?: number;
  refused_count?: number;
  cooldown_active?: boolean;
  recent_logs?: TelemetryLogItem[];
}

export async function getAiUsageSummary(limit = 20): Promise<ExtendedAIUsageStats> {
  try {
    const headers = getAuthHeaders();
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/agent/ai-usage?limit=${limit}`,
      { method: 'GET', headers },
      4000
    );
    if (!res.ok) throw new ApiError(res.status, 'Không thể tải thống kê AI');
    return await res.json();
  } catch {
    // Local fallback stats for offline/mock development
    return {
      total_requests: 42,
      total_tokens: 15420,
      total_input_tokens: 11200,
      total_output_tokens: 4220,
      total_cost_usd: 0.0078,
      avg_latency_ms: 1240,
      success_count: 38,
      fallback_count: 2,
      refused_count: 2,
      error_count: 0,
      cooldown_active: false,
      model_breakdown: {
        'gemini-3.5-flash-lite': 38,
        'seed_faq_bm25': 4,
      },
      recent_logs: [
        {
          id: 1,
          trace_id: 'tr-1042',
          endpoint: '/api/v1/chat',
          prompt_version: 'v2.1',
          provider: 'google',
          model_name: 'gemini-3.5-flash-lite',
          tools_called: ['lookup_customer_tickets'],
          prompt_tokens: 420,
          completion_tokens: 85,
          total_tokens: 505,
          latency_ms: 1180,
          cost_usd: 0.00032,
          status: 'success',
          created_at: new Date(Date.now() - 5 * 60000).toISOString(),
        },
        {
          id: 2,
          trace_id: 'tr-1041',
          endpoint: '/api/v1/agent/draft-reply',
          prompt_version: 'v1.4',
          provider: 'deterministic',
          model_name: 'seed_faq_bm25',
          tools_called: [],
          prompt_tokens: 180,
          completion_tokens: 40,
          total_tokens: 220,
          latency_ms: 85,
          cost_usd: 0.0,
          status: 'fallback',
          created_at: new Date(Date.now() - 22 * 60000).toISOString(),
        },
      ],
    };
  }
}

export async function resetAiCooldown(): Promise<ResetCooldownResponse> {
  const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/agent/ai-usage/reset-cooldown`,
    {
      method: 'POST',
      headers,
    },
    5000
  );
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errData.detail || 'Không thể đặt lại Cooldown Circuit Breaker');
  }
  return await res.json();
}

export async function getAiUsageLogs(filters?: {
  limit?: number;
  skip?: number;
}): Promise<TelemetryLogItem[]> {
  try {
    const summary = await getAiUsageSummary(filters?.limit || 20);
    return summary.recent_logs || [];
  } catch {
    return [];
  }
}

export async function checkBackendHealth(): Promise<{
  status: 'ok' | 'degraded' | 'offline';
  database?: string;
  version?: string;
}> {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/health`, { method: 'GET' }, 2500);
    if (!res.ok) return { status: 'offline' };
    const data = await res.json();
    return {
      status: data.status || 'ok',
      database: data.database,
      version: data.version,
    };
  } catch {
    return { status: 'offline' };
  }
}
