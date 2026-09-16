export type TabType = 'chat' | 'ticket' | 'agent';

export type UIState = 'success' | 'loading' | 'empty' | 'error';

export type TicketPriority = 'Low' | 'Medium' | 'High' | 'Urgent';

export type TicketCategory = 'Authentication' | 'Billing' | 'Bug Report' | 'Feature Request';

export type TicketStatus = 'Open' | 'Pending' | 'Resolved';

export interface Citation {
  code: string;
  link: string;
  doc_id?: string;
  title?: string;
  source_url?: string;
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
  escalation_recommended?: boolean;
}

export interface Ticket {
  id: string;
  ticket_code?: string;
  customer: string;
  email: string;
  subject: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  aiTag: string;
  ai_tags?: string[];
  date: string;
  slaTime: string;
  summary: string;
  draftReply: string;
  message: string;
  raw_id?: number;
  estimated_response_hours?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TicketFormData {
  fullName: string;
  email: string;
  category: TicketCategory;
  priority: TicketPriority;
  subject: string;
  message: string;
}

export interface TicketFormErrors {
  fullName?: string;
  email?: string;
  category?: string;
  priority?: string;
  subject?: string;
  message?: string;
}

export type ToastType = 'success' | 'error' | 'info' | 'warning' | 'loading' | 'empty';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

export interface BackendCitation {
  doc_id: string;
  title: string;
  source_url: string;
}

export interface BackendChatResponse {
  response: string;
  citations: BackendCitation[];
  latency_ms: number;
  confidence: number;
  is_fallback: boolean;
  escalation_recommended?: boolean;
}

export interface BackendTicketResponse {
  id: number;
  ticket_code: string;
  customer_name: string;
  customer_email: string;
  category: string;
  priority: string;
  subject: string;
  description: string;
  status: string;
  ai_tags: string[];
  ai_draft_reply: string | null;
  estimated_response_hours: number;
  created_at: string;
  updated_at?: string | null;
}

