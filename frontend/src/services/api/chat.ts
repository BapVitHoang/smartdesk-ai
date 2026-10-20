/**
 * Chat and RAG API Service
 * Handles synchronous and streaming customer queries with graceful fallback.
 */

import { Citation, BackendChatResponse } from '../../types';
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
        headers: { 'Content-Type': 'application/json' },
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
    let confidence = 0.85;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.delta) {
              accumulated += data.delta;
              onDelta(data.delta);
            }
            if (data.citations) {
              citations = data.citations;
            }
            if (data.is_fallback !== undefined) isFallback = data.is_fallback;
            if (data.confidence !== undefined) confidence = data.confidence;
          } catch {
            // raw string delta
            const rawChunk = line.slice(6);
            accumulated += rawChunk;
            onDelta(rawChunk);
          }
        }
      }
    }

    const elapsed = Math.round(performance.now() - startTime);
    return {
      response: accumulated,
      citations,
      latency_ms: elapsed,
      confidence,
      is_fallback: isFallback,
    };
  } catch (err) {
    // If stream fails, fallback to standard sendChatMessage
    return await sendChatMessage(message, sessionId, workspaceId, onToast);
  }
}
