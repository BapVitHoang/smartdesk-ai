/**
 * Support Ticket API Service
 * Handles ticket creation, listing, SLA calculation, and AI Copilot triage.
 */

import {
  Ticket,
  TicketFormData,
  TicketStatus,
  TicketPriority,
  TicketCategory,
  BackendTicketResponse,
} from '../../types';
import { INITIAL_TICKETS } from '../../data';
import {
  API_BASE_URL,
  ApiError,
  ToastNotifier,
  notifyFallback,
  fetchWithTimeout,
} from './client';

// Status Mapping Helpers
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

// SLA & Date Formatting Helpers
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

// Backend -> Frontend Ticket Mapper
export function mapBackendTicketToFrontend(item: BackendTicketResponse): Ticket {
  const priority = (item.priority || 'Medium') as TicketPriority;
  const category = (item.category || 'Authentication') as TicketCategory;
  const slaHours =
    item.estimated_response_hours ||
    (priority === 'Urgent' ? 2 : priority === 'High' ? 4 : priority === 'Medium' ? 8 : 24);

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
 * Create Support Ticket
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
          workspace_id: formData.workspace_id || 1,
          customer_name: formData.fullName,
          customer_email: formData.email,
          category: formData.category,
          priority: formData.priority,
          subject: formData.subject,
          description: formData.message,
        }),
      },
      10000
    );

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new ApiError(res.status, errData.detail || `Lỗi tạo ticket: HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const mappedTicket = mapBackendTicketToFrontend(data);

    localFallbackTickets = [mappedTicket, ...localFallbackTickets];
    return mappedTicket;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi tạo ticket: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }

    toastFn(
      'Không thể kết nối đến máy chủ. Ticket đã được lưu an toàn vào bộ nhớ cục bộ.',
      'warning'
    );

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
 * List and Filter Tickets
 * Endpoint: GET /api/v1/tickets
 */
export async function getTickets(
  filters?: {
    workspace_id?: number;
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
    if (filters?.workspace_id !== undefined) params.append('workspace_id', String(filters.workspace_id));
    if (filters?.status) params.append('status', filters.status);
    if (filters?.category) params.append('category', filters.category);
    if (filters?.priority) params.append('priority', filters.priority);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.skip !== undefined) params.append('skip', String(filters.skip));
    if (filters?.limit !== undefined) params.append('limit', String(filters.limit));

    const url = `${API_BASE_URL}/tickets${params.toString() ? `?${params.toString()}` : ''}`;
    const res = await fetchWithTimeout(url, { method: 'GET' }, 4000);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new ApiError(res.status, errData.detail || `Lỗi máy chủ: HTTP ${res.status}`);
    }

    const data: BackendTicketResponse[] = await res.json();
    const mapped = data.map(mapBackendTicketToFrontend);
    
    localFallbackTickets = mapped;
    return mapped;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi tải danh sách ticket: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }

    toastFn(
      'Không thể kết nối Backend để tải danh sách ticket. Đang sử dụng dữ liệu dự phòng.',
      'warning'
    );
    return localFallbackTickets;
  }
}

/**
 * Update Ticket Status & AI Draft
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
      const errData = await res.json().catch(() => ({}));
      throw new ApiError(res.status, errData.detail || `Lỗi máy chủ: HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const updated = mapBackendTicketToFrontend(data);

    localFallbackTickets = localFallbackTickets.map((t) =>
      t.id === cleanId || t.ticket_code === `#${cleanId}` ? updated : t
    );

    return updated;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi cập nhật ticket: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }

    toastFn(
      'Không thể cập nhật máy chủ. Đã ghi nhận thay đổi trên giao diện người dùng.',
      'warning'
    );

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
 * Regenerate AI Draft Reply (Copilot)
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
      8000
    );

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data: BackendTicketResponse = await res.json();
    const updated = mapBackendTicketToFrontend(data);

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
