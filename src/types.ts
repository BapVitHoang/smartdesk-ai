export type TabType = 'chat' | 'ticket' | 'agent' | 'knowledge';

export type UIState = 'success' | 'loading' | 'empty' | 'error';

export type TicketPriority = 'Low' | 'Medium' | 'High' | 'Urgent';

export type TicketCategory = 'Authentication' | 'Billing' | 'Bug Report' | 'Feature Request' | 'General';

export type TicketStatus = 'Open' | 'Pending' | 'Resolved';

export interface Citation {
  code: string;
  link: string;
  doc_id?: string;
  title?: string;
  source_url?: string;
  page?: number;
  snippet?: string;
}

export interface KnowledgeArticle {
  doc_id: string;
  category: string;
  title: string;
  content: string;
  source_url: string;
}

export interface Workspace {
  id: number;
  slug: string;
  name: string;
  industry: string;
  persona_name: string;
  tone_of_voice: string;
  business_rules: string;
  created_at: string;
}

export interface DocumentItem {
  id: number;
  workspace_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'verified' | 'published' | 'failed';
  chunk_count: number;
  created_at: string;
  updated_at?: string;
}

export interface DocumentChunk {
  id: number;
  chunk_id: string;
  chunk_index: number;
  page_number: number;
  title: string;
  content: string;
}

export interface VerificationItem {
  id: number;
  question: string;
  ground_truth: string;
  rag_answer: string;
  score: number;
  status: 'passed' | 'warning' | 'failed';
  reason?: string;
}

export interface VerificationReport {
  id: number;
  document_id: number;
  workspace_id: number;
  faithfulness_score: number;
  status: 'passed' | 'warning' | 'failed';
  created_at: string;
  items: VerificationItem[];
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

export interface Ticket {
  id: string;
  ticket_code?: string;
  workspace_id?: number;
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
  workspace_id?: number;
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

export interface BackendTicketResponse {
  id: number;
  workspace_id?: number;
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
