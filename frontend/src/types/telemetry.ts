export interface AIUsageLogItem {
  id: number;
  trace_id: string;
  endpoint: string;
  model_name: string;
  provider: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number;
  status: string;
  error_message?: string;
  user_email?: string;
  workspace_id?: number;
  created_at: string;
}

export interface AIUsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  fallback_count: number;
  error_count: number;
  model_breakdown: Record<string, number>;
}

export interface TokenUsageSummary {
  today_tokens: number;
  today_cost_usd: number;
  monthly_budget_usd: number;
  remaining_budget_usd: number;
}
