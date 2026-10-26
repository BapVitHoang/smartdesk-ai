export interface AIUsageLogItem {
  id: number;
  trace_id: string;
  endpoint: string;
  prompt_version?: string;
  model_name: string;
  provider: string;
  tools_called?: string[];
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
  total_input_tokens?: number;
  total_output_tokens?: number;
  total_cost_usd: number;
  avg_cost_usd?: number;
  avg_latency_ms: number;
  success_count?: number;
  fallback_count: number;
  refused_count?: number;
  error_count: number;
  cooldown_active?: boolean;
  model_breakdown: Record<string, number>;
  recent_logs?: AIUsageLogItem[];
}

export interface TokenUsageSummary {
  today_tokens: number;
  today_cost_usd: number;
  monthly_budget_usd: number;
  remaining_budget_usd: number;
}

export interface AIUsageSummaryResponse {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  fallback_count: number;
  refused_count: number;
  recent_logs: AIUsageLogItem[];
}

export interface ResetCooldownResponse {
  status: string;
  message: string;
  cooldown_active: boolean;
}
