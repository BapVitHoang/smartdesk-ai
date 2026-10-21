/**
 * Authentication API Service (Hybrid OAuth2 & Demo Login)
 */

import { User, AuthTokenResponse } from '../../types';
import {
  API_BASE_URL,
  ApiError,
  setAuthToken,
  fetchWithTimeout,
  getAuthHeaders,
  getAuthToken,
} from './client';

export async function loginDemo(email: string): Promise<AuthTokenResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/auth/demo-login`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    },
    4000
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err.detail || 'Đăng nhập demo thất bại');
  }

  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function loginWithGoogle(idToken: string): Promise<AuthTokenResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/auth/google`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    },
    5000
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err.detail || 'Xác thực Google thất bại');
  }

  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    const token = getAuthToken();
    if (!token) {
      // Auto-initiate default admin session if not logged in
      const defaultAuth = await loginDemo('admin@smartdesk.ai');
      return defaultAuth.user;
    }

    const headers = getAuthHeaders();
    const res = await fetchWithTimeout(`${API_BASE_URL}/auth/me`, { method: 'GET', headers }, 3000);
    if (!res.ok) {
      // Token might be expired, fallback to demo admin
      const defaultAuth = await loginDemo('admin@smartdesk.ai');
      return defaultAuth.user;
    }
    return await res.json();
  } catch {
    // Offline fallback user (default to admin)
    return {
      id: 1,
      email: 'admin@smartdesk.ai',
      full_name: 'SmartDesk Administrator',
      role: 'admin',
      is_active: true,
      created_at: new Date().toISOString(),
    };
  }
}

export function logout(): void {
  setAuthToken(null);
}
