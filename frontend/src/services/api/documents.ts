/**
 * Document Knowledge Base & Active Verification API Service
 */

import {
  KnowledgeArticle,
  DocumentItem,
  DocumentChunk,
  VerificationReport,
} from '../../types';
import {
  INITIAL_FAQ_ARTICLES,
  INITIAL_DOCUMENTS,
  INITIAL_VERIFICATION_REPORTS,
} from '../../data';
import {
  API_BASE_URL,
  ApiError,
  ToastNotifier,
  notifyFallback,
  fetchWithTimeout,
} from './client';

let localFallbackDocuments: DocumentItem[] = [...INITIAL_DOCUMENTS];
let localFallbackReports: Record<number, VerificationReport> = { ...INITIAL_VERIFICATION_REPORTS };

/**
 * Get Knowledge Base Article by ID
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

/**
 * Get Documents of Workspace
 * Endpoint: GET /api/v1/workspaces/{workspace_id}/documents
 */
export async function getDocuments(
  workspaceId: number,
  onToast?: ToastNotifier
): Promise<DocumentItem[]> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/workspaces/${workspaceId}/documents`,
      { method: 'GET' },
      4000
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: DocumentItem[] = await res.json();
    return data;
  } catch {
    const toastFn = onToast || notifyFallback;
    toastFn('Chế độ ngoại tuyến: Nạp danh sách tài liệu từ bộ nhớ đệm.', 'info');
    return localFallbackDocuments.filter((d) => d.workspace_id === workspaceId);
  }
}

/**
 * Get Document Chunks
 * Endpoint: GET /api/v1/documents/{document_id}/chunks
 */
export async function getDocumentChunks(
  documentId: number,
  onToast?: ToastNotifier
): Promise<DocumentChunk[]> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/documents/${documentId}/chunks`,
      { method: 'GET' },
      4000
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    const toastFn = onToast || notifyFallback;
    toastFn('Hiển thị trích đoạn mẫu từ bộ nhớ đệm ngoại tuyến.', 'info');
    return [
      {
        id: 1,
        chunk_id: `doc-${documentId}-chk-1`,
        chunk_index: 0,
        page_number: 1,
        title: `Tài liệu #${documentId} - Đoạn 1`,
        content: 'Nội dung trích đoạn hiển thị từ bộ nhớ đệm ngoại tuyến.',
      },
    ];
  }
}

/**
 * Upload Document
 * Endpoint: POST /api/v1/workspaces/{workspace_id}/documents/upload
 */
export async function uploadDocument(
  workspaceId: number,
  file: File,
  onToast?: ToastNotifier
): Promise<DocumentItem> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/workspaces/${workspaceId}/documents/upload`,
      {
        method: 'POST',
        body: formData,
      },
      12000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const doc: DocumentItem = await res.json();
    localFallbackDocuments.unshift(doc);
    return doc;
  } catch (error: any) {
    const toastFn = onToast || notifyFallback;
    toastFn(`Ngoại tuyến: Lưu tạm tệp ${file.name} vào kho cục bộ.`, 'warning');
    const mockDoc: DocumentItem = {
      id: Date.now(),
      workspace_id: workspaceId,
      filename: file.name,
      file_type: file.name.split('.').pop() || 'txt',
      file_size: file.size,
      status: 'pending',
      chunk_count: 3,
      created_at: new Date().toISOString(),
    };
    localFallbackDocuments.unshift(mockDoc);
    return mockDoc;
  }
}

/**
 * Delete Document
 * Endpoint: DELETE /api/v1/documents/{document_id}
 */
export async function deleteDocument(
  documentId: number,
  onToast?: ToastNotifier
): Promise<boolean> {
  const toastFn = onToast || notifyFallback;
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/documents/${documentId}`,
      { method: 'DELETE' },
      4000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
    }
    localFallbackDocuments = localFallbackDocuments.filter((d) => d.id !== documentId);
    return true;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi xóa tài liệu: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }
    toastFn('Không thể kết nối máy chủ để xóa tài liệu.', 'warning');
    throw error;
  }
}

/**
 * Verify Document with Active Verification Engine
 */
export async function verifyDocument(
  documentId: number,
  onToast?: ToastNotifier
): Promise<VerificationReport> {
  const toastFn = onToast || notifyFallback;
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/documents/${documentId}/verify`,
      { method: 'POST' },
      15000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
    }
    const report: VerificationReport = await res.json();
    localFallbackReports[documentId] = report;
    const doc = localFallbackDocuments.find((d) => d.id === documentId);
    if (doc) doc.status = report.status === 'failed' ? 'failed' : 'verified';
    return report;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi sát hạch tài liệu: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }
    toastFn('Không thể kết nối máy chủ để sát hạch tài liệu.', 'warning');
    throw error;
  }
}

/**
 * Get Document Verification Report
 */
export async function getVerificationReport(
  documentId: number,
  onToast?: ToastNotifier
): Promise<VerificationReport> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/documents/${documentId}/verification-report`,
      { method: 'GET' },
      4000
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    if (localFallbackReports[documentId]) {
      return localFallbackReports[documentId];
    }
    throw new Error('Chưa có báo cáo sát hạch cho tài liệu này.');
  }
}

/**
 * Publish Document
 */
export async function publishDocument(
  documentId: number,
  onToast?: ToastNotifier
): Promise<boolean> {
  const toastFn = onToast || notifyFallback;
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/documents/${documentId}/publish`,
      { method: 'POST' },
      4000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `HTTP ${res.status}`);
    }
    const doc = localFallbackDocuments.find((d) => d.id === documentId);
    if (doc) doc.status = 'published';
    return true;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi xuất bản: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }
    toastFn('Không thể kết nối máy chủ để xuất bản tài liệu.', 'warning');
    throw error;
  }
}
