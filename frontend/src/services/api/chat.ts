/**
 * Chat and RAG API Service
 * Handles synchronous and streaming customer queries with graceful fallback.
 */

import { Citation, BackendChatResponse, PendingAction } from '../../types';
import { getRagResponse } from '../../data';
import {
  API_BASE_URL,
  ApiError,
  ToastNotifier,
  notifyFallback,
  fetchWithTimeout,
  getAuthHeaders,
} from './client';

export interface ChatResult {
  response: string;
  citations: Citation[];
  bulletPoints?: string[];
  latency_ms: number;
  confidence: number;
  is_fallback: boolean;
  fallback_reason?: string;
  escalation_recommended?: boolean;
  pending_action?: PendingAction;
  tools_called?: string[];
}

export interface ConfirmActionResult {
  action_id: string;
  status: string;
  executed: boolean;
  result_message: string;
  message: string;
  ticket_id?: string;
  data?: Record<string, unknown>;
  result_data?: Record<string, unknown>;
}

/**
 * 1. Send Chat Message (RAG Query) with Automatic Fallback
 * Endpoint: POST /api/v1/chat
 */
export async function sendChatMessage(
  message: string,
  sessionId?: string,
  workspaceId?: number,
  onToast?: ToastNotifier
): Promise<ChatResult> {
  const startTime = performance.now();

  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/chat`,
      {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          message,
          session_id: sessionId || `sess-${Date.now().toString(36)}`,
          workspace_id: workspaceId || 1,
        }),
      },
      8000
    );

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new ApiError(res.status, errData.detail || `Lỗi máy chủ: HTTP ${res.status}`);
    }

    const data: BackendChatResponse = await res.json();
    const elapsed = Math.round(data.latency_ms || performance.now() - startTime);

    if (data.fallback_reason === 'FREE_TIER_RATE_LIMIT_COOLDOWN') {
      const toastFn = onToast || notifyFallback;
      toastFn(
        'Đang kích hoạt chế độ bảo vệ chi phí (Chạm hạn mức Free Tier 15 RPM). Hệ thống chuyển sang tra cứu nội bộ miễn phí trong 60 giây.',
        'warning'
      );
    }

    // Map backend citations to format: "[doc_id: title]"
    const citations: Citation[] = (data.citations || []).map((c) => ({
      code: c.page ? `${c.title} (Trang ${c.page})` : `${c.doc_id}: ${c.title}`,
      link: c.source_url || '#',
      doc_id: c.doc_id,
      title: c.title,
      source_url: c.source_url,
      page: c.page,
      snippet: c.snippet,
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
      fallback_reason: data.fallback_reason,
      escalation_recommended: data.escalation_recommended,
      pending_action: data.pending_action,
      tools_called: data.tools_called,
    };
  } catch (error: any) {
    if (error instanceof ApiError) {
      const toastFn = onToast || notifyFallback;
      toastFn(error.detail || `Lỗi máy chủ: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }

    const elapsed = Math.round(performance.now() - startTime);
    const toastFn = onToast || notifyFallback;
    toastFn(
      'Mất kết nối Backend AI hoặc máy chủ đang ngoại tuyến. Đã tự động kích hoạt mô hình tra cứu dự phòng.',
      'warning'
    );

    // Fallback to local deterministic RAG response from data.ts
    const localRag = getRagResponse(message, workspaceId || 1);
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
 * 2. Stream Chat Message (Server-Sent Events)
 * Endpoint: POST /api/v1/chat/stream
 */
export async function streamChatMessage(
  message: string,
  onDelta: (chunk: string) => void,
  sessionId?: string,
  workspaceId?: number,
  onToast?: ToastNotifier
): Promise<ChatResult> {
  const startTime = performance.now();
  try {
    const res = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        message,
        session_id: sessionId || `sess-${Date.now().toString(36)}`,
        workspace_id: workspaceId || 1,
      }),
    });

    if (!res.ok || !res.body) {
      // Fallback to regular chat if streaming endpoint not ready
      return await sendChatMessage(message, sessionId, workspaceId, onToast);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let accumulated = '';
    let citations: Citation[] = [];
    let isFallback = false;
    let fallbackReason: string | undefined = undefined;
    let confidence = 0.85;
    let escalationRecommended: boolean | undefined = undefined;
    let pendingAction: PendingAction | undefined = undefined;
    let toolsCalled: string[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'metadata') {
              if (data.citations) {
                citations = (data.citations || []).map((c: any) => ({
                  code: c.page ? `${c.title} (Trang ${c.page})` : `${c.doc_id}: ${c.title}`,
                  link: c.source_url || '#',
                  doc_id: c.doc_id,
                  title: c.title,
                  source_url: c.source_url,
                  page: c.page,
                  snippet: c.snippet,
                }));
              }
              if (data.confidence !== undefined) confidence = data.confidence;
              if (data.is_fallback !== undefined) isFallback = data.is_fallback;
              if (data.escalation_recommended !== undefined) escalationRecommended = data.escalation_recommended;
              if (data.pending_action) pendingAction = data.pending_action;
              if (data.tools_called) toolsCalled = data.tools_called;
            } else if (data.type === 'token' || data.delta) {
              const deltaStr = data.token || data.delta || '';
              accumulated += deltaStr;
              onDelta(deltaStr);
            } else if (data.type === 'done') {
              if (data.response) accumulated = data.response;
              if (data.citations && data.citations.length > 0) {
                citations = data.citations.map((c: any) => ({
                  code: c.page ? `${c.title} (Trang ${c.page})` : `${c.doc_id}: ${c.title}`,
                  link: c.source_url || '#',
                  doc_id: c.doc_id,
                  title: c.title,
                  source_url: c.source_url,
                  page: c.page,
                  snippet: c.snippet,
                }));
              }
              if (data.is_fallback !== undefined) isFallback = data.is_fallback;
              if (data.fallback_reason) fallbackReason = data.fallback_reason;
              if (data.confidence !== undefined) confidence = data.confidence;
              if (data.escalation_recommended !== undefined) escalationRecommended = data.escalation_recommended;
              if (data.pending_action) pendingAction = data.pending_action;
              if (data.tools_called) toolsCalled = data.tools_called;
            }
          } catch {
            const rawChunk = line.slice(6);
            accumulated += rawChunk;
            onDelta(rawChunk);
          }
        }
      }
    }

    const elapsed = Math.round(performance.now() - startTime);

    // Extract bullet points if present in response markdown
    const bulletPoints: string[] = [];
    const lines = accumulated.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-*•]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
        bulletPoints.push(trimmed.replace(/^[-*•\d.]+\s+/, ''));
      }
    }

    return {
      response: accumulated,
      citations,
      bulletPoints: bulletPoints.length > 0 ? bulletPoints : undefined,
      latency_ms: elapsed,
      confidence,
      is_fallback: isFallback,
      fallback_reason: fallbackReason,
      escalation_recommended: escalationRecommended,
      pending_action: pendingAction,
      tools_called: toolsCalled.length > 0 ? toolsCalled : undefined,
    };
  } catch (err) {
    // If stream fails, fallback to standard sendChatMessage
    return await sendChatMessage(message, sessionId, workspaceId, onToast);
  }
}

/**
 * 3. Confirm or Reject Pending Agent Tool Action (REQ-14)
 * Endpoint: POST /api/v1/chat/confirm-action
 */
export async function confirmChatAction(
  actionId: string,
  confirmed: boolean,
  onToast?: ToastNotifier
): Promise<ConfirmActionResult> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/chat/confirm-action`,
      {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          action_id: actionId,
          confirmed,
        }),
      },
      8000
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `Lỗi xác nhận công cụ: HTTP ${res.status}`);
    }

    const data: ConfirmActionResult = await res.json();
    return data;
  } catch (error: any) {
    if (error instanceof ApiError) {
      const toastFn = onToast || notifyFallback;
      toastFn(error.detail || `Lỗi máy chủ: HTTP ${error.statusCode}`, 'error');
      throw error;
    }
    const toastFn = onToast || notifyFallback;
    toastFn('Không thể kết nối đến máy chủ để xác nhận thao tác.', 'warning');
    throw error;
  }
}
