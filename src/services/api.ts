/**
 * SmartDesk AI - API Client Module
 * Connects frontend to FastAPI asynchronous backend (/api/v1)
 * with robust graceful fallback when the backend is offline.
 */

import {
  Ticket,
  TicketFormData,
  TicketStatus,
  TicketPriority,
  TicketCategory,
  Citation,
  ToastType,
  BackendChatResponse,
  BackendTicketResponse,
  KnowledgeArticle,
} from '../types';
import { INITIAL_TICKETS, INITIAL_FAQ_ARTICLES, getRagResponse } from '../data';

// 1. Base URL Configuration
export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';

// 2. Global Toast Notifier for graceful fallback warnings
export type ToastNotifier = (msg: string, type?: ToastType) => void;
let globalToastNotifier: ToastNotifier | null = null;

export function registerApiToastHandler(fn: ToastNotifier | null) {
  globalToastNotifier = fn;
}

function notifyFallback(msg: string, type: ToastType = 'warning') {
  if (globalToastNotifier) {
    globalToastNotifier(msg, type);
  }
}

// 3. Status Mapping Helpers
export function mapBackendStatusToFrontend(backendStatus: string): TicketStatus {
  const s = (backendStatus || '').toLowerCase();
  if (s === 'in_progress') return 'Pending';
  if (s === 'resolved' || s === 'closed') return 'Resolved';
  return 'Open';
}

export function mapFrontendStatusToBackend(frontendStatus: TicketStatus): string {
  if (frontendStatus === 'Pending') return 'in_progress';
  if (frontendStatus === 'Resolved') return 'resolved';
  return 'open';
}

// 4. SLA & Date Formatting Helpers
export function formatSla(hours: number, priority: string): string {
  const pLevel =
    priority === 'Urgent' ? 'P1' : priority === 'High' ? 'P2' : priority === 'Medium' ? 'P3' : 'P4';
  return `${hours} giờ làm việc (Cam kết SLA ${pLevel})`;
}

export function formatTicketDate(isoDate?: string | null): string {
  if (!isoDate) return 'Vừa xong';
  try {
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return 'Vừa xong';
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return isToday ? `${timeStr} - Hôm nay` : `${timeStr} - ${d.toLocaleDateString()}`;
  } catch {
    return 'Vừa xong';
  }
}

// 5. Backend -> Frontend Ticket Mapper
export function mapBackendTicketToFrontend(item: BackendTicketResponse): Ticket {
  const priority = (item.priority || 'Medium') as TicketPriority;
  const category = (item.category || 'Authentication') as TicketCategory;
  const slaHours =
    item.estimated_response_hours ||
    (priority === 'Urgent' ? 2 : priority === 'High' ? 4 : priority === 'Medium' ? 8 : 24);

  // id without '#' for clean #{t.id} template rendering
  const cleanId = item.ticket_code ? item.ticket_code.replace(/^#/, '') : `TICK-${item.id}`;

  return {
    id: cleanId,
    ticket_code: item.ticket_code || `#${cleanId}`,
    raw_id: item.id,
    customer: item.customer_name,
    email: item.customer_email,
    subject: item.subject,
    category,
    priority,
    status: mapBackendStatusToFrontend(item.status),
    aiTag:
      item.ai_tags && item.ai_tags.length > 0
        ? item.ai_tags.slice(0, 2).join(' / ')
        : `${category} / ${priority}`,
    ai_tags: item.ai_tags || [],
    date: formatTicketDate(item.created_at),
    slaTime: formatSla(slaHours, priority),
    summary: `Yêu cầu từ ${item.customer_name}. Phân tích: ${category} (${priority}).`,
    draftReply: item.ai_draft_reply || '',
    message: item.description,
    estimated_response_hours: slaHours,
    created_at: item.created_at,
    updated_at: item.updated_at || undefined,
  };
}

// In-memory fallback ticket store to preserve offline created/updated tickets
let localFallbackTickets: Ticket[] = [...INITIAL_TICKETS];

/**
 * Fetch with configurable timeout and abort controller
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 5000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

/**
 * 1. Send Chat Message (RAG Query) with Automatic Fallback
 * Endpoint: POST /api/v1/chat
 */
export async function sendChatMessage(
  message: string,
  sessionId?: string,
  onToast?: ToastNotifier
): Promise<{
  response: string;
  citations: Citation[];
  bulletPoints?: string[];
  latency_ms: number;
  confidence: number;
  is_fallback: boolean;
  escalation_recommended?: boolean;
}> {
  const startTime = performance.now();

  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/chat`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: sessionId || `sess-${Date.now().toString(36)}`,
        }),
      },
      4500
    );

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: HTTP ${res.status}`);
    }

    const data: BackendChatResponse = await res.json();
    const elapsed = Math.round(data.latency_ms || performance.now() - startTime);

    // Map backend citations to format: "[doc_id: title]"
    const citations: Citation[] = (data.citations || []).map((c) => ({
      code: `${c.doc_id}: ${c.title}`,
      link: c.source_url || '#',
      doc_id: c.doc_id,
      title: c.title,
      source_url: c.source_url,
    }));

    // Extract bullet points if present in response markdown
    const bulletPoints: string[] = [];
    const lines = data.response.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-*•]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
        bulletPoints.push(trimmed.replace(/^[-*•\d.]+\s+/, ''));
      }
    }

    return {
      response: data.response,
      citations,
      bulletPoints: bulletPoints.length > 0 ? bulletPoints : undefined,
      latency_ms: elapsed,
      confidence: data.confidence,
      is_fallback: data.is_fallback,
      escalation_recommended: data.escalation_recommended,
    };
  } catch (error: any) {
    const elapsed = Math.round(performance.now() - startTime);
    const toastFn = onToast || notifyFallback;
    toastFn(
      'Mất kết nối Backend AI hoặc máy chủ đang ngoại tuyến. Đã tự động kích hoạt mô hình tra cứu dự phòng.',
      'warning'
    );

    // Fallback to local deterministic RAG response from data.ts
    const localRag = getRagResponse(message);
    return {
      response: localRag.text,
      citations: localRag.citations.map((c) => ({
        code: c.code,
        link: c.link,
      })),
      bulletPoints: localRag.bulletPoints,
      latency_ms: elapsed || 1100,
      confidence: 0.75,
      is_fallback: true,
      escalation_recommended: false,
    };
  }
}

/**
 * 2. Create Support Ticket
 * Endpoint: POST /api/v1/tickets
 */
export async function createTicket(
  formData: TicketFormData,
  onToast?: ToastNotifier
): Promise<Ticket> {
  const toastFn = onToast || notifyFallback;

  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/tickets`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: formData.fullName,
          customer_email: formData.email,
          category: formData.category,
          priority: formData.priority,
          subject: formData.subject,
          description: formData.message,
        }),
      },
      4500
    );

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const mappedTicket = mapBackendTicketToFrontend(data);

    // Cache locally as well
    localFallbackTickets = [mappedTicket, ...localFallbackTickets];
    return mappedTicket;
  } catch (error: any) {
    toastFn(
      'Không thể kết nối đến máy chủ. Ticket đã được lưu an toàn vào bộ nhớ cục bộ.',
      'warning'
    );

    // Graceful Fallback: generate formatted local ticket
    const randomCode = `TICK-${Math.floor(1000 + Math.random() * 9000)}`;
    const slaCommitment =
      formData.priority === 'Urgent'
        ? '2 giờ làm việc (Cam kết SLA P1)'
        : formData.priority === 'High'
        ? '4 giờ làm việc (Cam kết SLA P2)'
        : formData.priority === 'Medium'
        ? '8 giờ làm việc (Cam kết SLA P3)'
        : '24 giờ làm việc (Cam kết SLA P4)';

    const localTicket: Ticket = {
      id: randomCode,
      ticket_code: `#${randomCode}`,
      customer: formData.fullName,
      email: formData.email,
      subject: formData.subject,
      category: formData.category,
      priority: formData.priority,
      status: 'Open',
      aiTag: `${formData.category.slice(0, 4)} / ${formData.priority}`,
      ai_tags: [formData.category, formData.priority, 'Local Offline'],
      date: 'Vừa xong',
      slaTime: slaCommitment,
      summary: `Ticket tạo bởi ${formData.fullName}. Phân loại sơ bộ: ${formData.category}.`,
      draftReply: `Xin chào ${formData.fullName}, SmartDesk AI đã tiếp nhận yêu cầu #${randomCode} về vấn đề "${formData.subject}". Đội ngũ kỹ thuật đang xử lý theo cam kết SLA ${slaCommitment}.`,
      message: formData.message,
    };

    localFallbackTickets = [localTicket, ...localFallbackTickets];
    return localTicket;
  }
}

/**
 * 3. List and Filter Tickets
 * Endpoint: GET /api/v1/tickets
 */
export async function getTickets(
  filters?: {
    status?: string;
    category?: string;
    priority?: string;
    search?: string;
    skip?: number;
    limit?: number;
  },
  onToast?: ToastNotifier
): Promise<Ticket[]> {
  const toastFn = onToast || notifyFallback;

  try {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.priority) params.append('priority', filters.priority);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.skip !== undefined) params.append('skip', String(filters.skip));
    if (filters?.limit !== undefined) params.append('limit', String(filters.limit));

    const url = `${API_BASE_URL}/tickets${params.toString() ? `?${params.toString()}` : ''}`;
    const res = await fetchWithTimeout(url, { method: 'GET' }, 4000);

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data: BackendTicketResponse[] = await res.json();
    const mapped = data.map(mapBackendTicketToFrontend);
    
    // Update local cache
    localFallbackTickets = mapped;
    return mapped;
  } catch (error: any) {
    toastFn(
      'Không thể kết nối Backend để tải danh sách ticket. Đang sử dụng dữ liệu dự phòng.',
      'warning'
    );
    return localFallbackTickets;
  }
}

/**
 * 4. Update Ticket Status & AI Draft
 * Endpoint: PATCH /api/v1/tickets/{ticket_id}
 */
export async function updateTicketStatus(
  ticketId: string | number,
  status: TicketStatus,
  aiDraftReply?: string,
  onToast?: ToastNotifier
): Promise<Ticket> {
  const toastFn = onToast || notifyFallback;
  const cleanId = String(ticketId).replace(/^#/, '');

  try {
    const backendStatus = mapFrontendStatusToBackend(status);
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/tickets/${encodeURIComponent(cleanId)}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: backendStatus,
          ai_draft_reply: aiDraftReply,
        }),
      },
      4500
    );

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const updated = mapBackendTicketToFrontend(data);

    // Sync in-memory fallback
    localFallbackTickets = localFallbackTickets.map((t) =>
      t.id === cleanId || t.ticket_code === `#${cleanId}` ? updated : t
    );

    return updated;
  } catch (error: any) {
    toastFn(
      'Không thể cập nhật máy chủ. Đã ghi nhận thay đổi trên giao diện người dùng.',
      'warning'
    );

    // Update in local fallback list
    let matchedTicket: Ticket | undefined = localFallbackTickets.find(
      (t) => t.id === cleanId || t.ticket_code === `#${cleanId}`
    );

    if (matchedTicket) {
      matchedTicket = {
        ...matchedTicket,
        status,
        draftReply: aiDraftReply !== undefined ? aiDraftReply : matchedTicket.draftReply,
      };
      localFallbackTickets = localFallbackTickets.map((t) =>
        t.id === cleanId ? matchedTicket! : t
      );
      return matchedTicket;
    }

    // Return dummy object if not in list
    return {
      id: cleanId,
      ticket_code: `#${cleanId}`,
      customer: 'Khách hàng',
      email: 'customer@example.com',
      subject: 'Yêu cầu hỗ trợ',
      category: 'Authentication',
      priority: 'Medium',
      status,
      aiTag: 'General / Medium',
      date: 'Vừa xong',
      slaTime: '8 giờ làm việc',
      summary: 'Cập nhật trạng thái ngoại tuyến',
      draftReply: aiDraftReply || '',
      message: '',
    };
  }
}

/**
 * 5. Regenerate AI Draft Reply (Copilot)
 * Endpoint: POST /api/v1/agent/tickets/{ticket_id}/generate-draft
 */
export async function regenerateAiDraft(
  ticketId: string | number,
  onToast?: ToastNotifier
): Promise<Ticket> {
  const toastFn = onToast || notifyFallback;
  const cleanId = String(ticketId).replace(/^#/, '');

  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/agent/tickets/${encodeURIComponent(cleanId)}/generate-draft`,
      {
        method: 'POST',
      },
      4500
    );

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const updated = mapBackendTicketToFrontend(data);

    // Sync in-memory fallback
    localFallbackTickets = localFallbackTickets.map((t) =>
      t.id === cleanId || t.ticket_code === `#${cleanId}` ? updated : t
    );

    return updated;
  } catch (error: any) {
    toastFn(
      'Máy chủ ngoại tuyến, AI Copilot đã tạo bản thảo phản hồi cục bộ.',
      'warning'
    );

    let matched = localFallbackTickets.find(
      (t) => t.id === cleanId || t.ticket_code === `#${cleanId}`
    );

    const generatedDraft = matched
      ? `Xin chào ${matched.customer},\n\nSmartDesk AI Copilot đã xem xét lại yêu cầu hỗ trợ #${matched.id} của bạn về "${matched.subject}".\n\n1. Đội ngũ chuyên trách đã kích hoạt kiểm tra nhật ký bảo mật và quy trình đối soát.\n2. Vui lòng cung cấp thêm ảnh chụp màn hình hoặc mã lỗi cụ thể nếu có để chúng tôi xử lý nhanh nhất.\n\nTrân trọng,\nĐội ngũ Kỹ thuật SmartDesk AI`
      : 'Xin chào, SmartDesk AI Copilot đã cập nhật câu trả lời đề xuất.';

    if (matched) {
      matched = { ...matched, draftReply: generatedDraft };
      localFallbackTickets = localFallbackTickets.map((t) =>
        t.id === cleanId ? matched! : t
      );
      return matched;
    }

    return {
      id: cleanId,
      ticket_code: `#${cleanId}`,
      customer: 'Khách hàng',
      email: 'customer@example.com',
      subject: 'Yêu cầu hỗ trợ',
      category: 'Authentication',
      priority: 'Medium',
      status: 'Open',
      aiTag: 'General / Medium',
      date: 'Vừa xong',
      slaTime: '8 giờ làm việc',
      summary: 'Bản thảo tạo ngoại tuyến',
      draftReply: generatedDraft,
      message: '',
    };
  }
}

/**
 * 6. Health Check Probe
 * Endpoint: GET /api/v1/health
 */
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

/**
 * 7. Get Knowledge Base Article by ID
 * Endpoint: GET /api/v1/knowledge/{doc_id}
 */
export async function getKnowledgeArticle(
  docId: string,
  onToast?: ToastNotifier
): Promise<KnowledgeArticle> {
  const toastFn = onToast || notifyFallback;

  // Normalize candidate doc_ids (e.g. "faq-01", "doc-01", "faq-02: Two-Factor...")
  const cleanDocId = (docId || '').split(':')[0].trim().toLowerCase().replace(/^#/, '');
  const candidates: string[] = [cleanDocId];
  if (cleanDocId.startsWith('doc-')) {
    candidates.push(cleanDocId.replace('doc-', 'faq-'));
  } else if (cleanDocId.startsWith('faq-')) {
    candidates.push(cleanDocId.replace('faq-', 'doc-'));
  }
  const digitMatch = cleanDocId.match(/\d+/);
  if (digitMatch) {
    const num = parseInt(digitMatch[0], 10);
    const paddedFaq = num < 10 ? `faq-0${num}` : `faq-${num}`;
    const paddedDoc = num < 10 ? `doc-0${num}` : `doc-${num}`;
    if (!candidates.includes(paddedFaq)) candidates.push(paddedFaq);
    if (!candidates.includes(paddedDoc)) candidates.push(paddedDoc);
  }

  // Attempt backend API call with candidate doc_ids
  for (const candidate of candidates) {
    try {
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/knowledge/${encodeURIComponent(candidate)}`,
        { method: 'GET' },
        3000
      );
      if (res.ok) {
        const article: KnowledgeArticle = await res.json();
        return article;
      }
    } catch {
      // Continue to next candidate or fallback
    }
  }

  // Fallback to local INITIAL_FAQ_ARTICLES
  toastFn('Đang xem bài viết từ kho tri thức nội bộ SmartDesk (Chế độ Ngoại tuyến).', 'info');

  const localMatch = INITIAL_FAQ_ARTICLES.find((art) => {
    const artId = art.doc_id.toLowerCase();
    const artTitle = art.title.toLowerCase();
    return (
      candidates.some((c) => artId === c || artId.includes(c) || c.includes(artId)) ||
      artTitle.includes(cleanDocId) ||
      cleanDocId.includes(artTitle.slice(0, 15).toLowerCase())
    );
  });

  if (localMatch) {
    return localMatch;
  }

  return INITIAL_FAQ_ARTICLES[0];
}

