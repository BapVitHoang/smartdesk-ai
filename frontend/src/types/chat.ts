export interface Citation {
  code: string;
  link: string;
  doc_id?: string;
  title?: string;
  source_url?: string;
  page?: number;
  snippet?: string;
}

export interface BackendCitation {
  doc_id: string;
  title: string;
  source_url: string;
  page?: number;
  snippet?: string;
}

export interface BackendChatResponse {
  response: string;
  citations: BackendCitation[];
  latency_ms: number;
  confidence: number;
  is_fallback: boolean;
  fallback_reason?: string;
  escalation_recommended?: boolean;
  pending_action?: PendingAction;
  tools_called?: string[];
}

export interface ChatMessage {
  id?: string;
  sender: 'bot' | 'user';
  text: string;
  bulletPoints?: string[];
  citations?: Citation[];
  time: string;
  feedbackGiven?: 'thumb_up' | 'thumb_down' | null;
  latency_ms?: number;
  confidence?: number;
  is_fallback?: boolean;
  fallback_reason?: string;
  escalation_recommended?: boolean;
  workspace_id?: number;
  pending_action?: PendingAction;
  tools_called?: string[];
}

export interface PendingAction {
  action_id: string;
  action_type: 'create_escalation_ticket' | 'update_ticket_priority_or_status';
  summary: string;
  parameters: Record<string, unknown>;
  requires_confirmation: boolean;
  expires_at?: string;
}

export interface ConfirmActionRequest {
  action_id: string;
  confirmed: boolean;
}

export interface ConfirmActionResponse {
  action_id: string;
  status: 'executed' | 'cancelled';
  result_message: string;
  ticket_id?: string;
  data?: Record<string, unknown>;
}

export interface SSEMetadataEvent {
  session_id?: string;
  model: string;
  prompt_version: string;
}

export interface SSETokenEvent {
  token: string;
}

export interface SSEDoneEvent {
  response: string;
  citations: BackendCitation[];
  latency_ms: number;
  confidence: number;
  is_fallback: boolean;
  fallback_reason?: string;
  escalation_recommended?: boolean;
  pending_action?: PendingAction;
  tools_called?: string[];
}

export interface ChatStreamEvent {
  delta?: string;
  done?: boolean;
  citations?: Citation[];
  latency_ms?: number;
  confidence?: number;
  is_fallback?: boolean;
  fallback_reason?: string;
  escalation_recommended?: boolean;
  error?: string;
}
