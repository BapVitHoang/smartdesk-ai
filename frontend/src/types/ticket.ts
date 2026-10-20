export type TicketPriority = 'Low' | 'Medium' | 'High' | 'Urgent';

export type TicketCategory = 'Authentication' | 'Billing' | 'Bug Report' | 'Feature Request' | 'General';

export type TicketStatus = 'Open' | 'Pending' | 'Resolved';

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
