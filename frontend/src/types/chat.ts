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
