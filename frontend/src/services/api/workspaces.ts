/**
 * Workspaces & Multi-Tenant Persona API Service
 */

import { Workspace } from '../../types';
import { INITIAL_WORKSPACES } from '../../data';
import {
  API_BASE_URL,
  ApiError,
  ToastNotifier,
  notifyFallback,
  fetchWithTimeout,
  getAuthHeaders,
} from './client';

let localFallbackWorkspaces: Workspace[] = [...INITIAL_WORKSPACES];

export async function getWorkspaces(onToast?: ToastNotifier): Promise<Workspace[]> {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/workspaces`, { method: 'GET' }, 3500);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: Workspace[] = await res.json();
    localFallbackWorkspaces = data;
    return data;
  } catch {
    const toastFn = onToast || notifyFallback;
    toastFn('Chế độ ngoại tuyến: Nạp danh sách doanh nghiệp cục bộ.', 'info');
    return localFallbackWorkspaces;
  }
}

export async function createWorkspace(
  payload: Partial<Workspace>,
  onToast?: ToastNotifier
): Promise<Workspace> {
  const toastFn = onToast || notifyFallback;
  try {
    const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/workspaces`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      },
      4000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `Lỗi tạo workspace: HTTP ${res.status}`);
    }
    const data: Workspace = await res.json();
    localFallbackWorkspaces.push(data);
    return data;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi tạo doanh nghiệp: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }
    toastFn(`Tạo doanh nghiệp cục bộ: ${error.message || ''}`, 'warning');
    const newWs: Workspace = {
      id: Date.now(),
      slug: payload.slug || `ws-${Date.now()}`,
      name: payload.name || 'Doanh Nghiệp Mới',
      industry: payload.industry || 'Chung',
      persona_name: payload.persona_name || 'AI Assistant',
      tone_of_voice: payload.tone_of_voice || 'Chuyên nghiệp',
      business_rules: payload.business_rules || '',
      created_at: new Date().toISOString(),
    };
    localFallbackWorkspaces.push(newWs);
    return newWs;
  }
}

export async function updateWorkspace(
  id: number,
  payload: Partial<Workspace>,
  onToast?: ToastNotifier
): Promise<Workspace> {
  const toastFn = onToast || notifyFallback;
  try {
    const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/workspaces/${id}`,
      {
        method: 'PUT',
        headers,
        body: JSON.stringify(payload),
      },
      4000
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new ApiError(res.status, err.detail || `Lỗi cập nhật workspace: HTTP ${res.status}`);
    }
    const updated: Workspace = await res.json();
    const idx = localFallbackWorkspaces.findIndex((w) => w.id === id);
    if (idx !== -1) {
      localFallbackWorkspaces[idx] = updated;
    }
    return updated;
  } catch (error: any) {
    if (error instanceof ApiError) {
      toastFn(error.detail || `Lỗi cập nhật doanh nghiệp: HTTP ${error.statusCode}`, 'warning');
      throw error;
    }
    toastFn('Đã cập nhật thông số doanh nghiệp (Chế độ Ngoại tuyến).', 'info');
    const idx = localFallbackWorkspaces.findIndex((w) => w.id === id);
    if (idx !== -1) {
      localFallbackWorkspaces[idx] = { ...localFallbackWorkspaces[idx], ...payload };
      return localFallbackWorkspaces[idx];
    }
    throw new Error('Workspace not found');
  }
}
