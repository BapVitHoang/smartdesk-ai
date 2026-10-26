/**
 * Authentication API Service (Google Identity Services & Demo Login)
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

/**
 * 1-Click Demo Login (strictly allowed in non-production environments).
 */
export async function loginDemo(email: string): Promise<AuthTokenResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/auth/oauth2/login`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'demo', email }),
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

/**
 * Real Google Identity Services (GIS) Login with Verified ID Token.
 */
export async function loginWithGoogle(credential: string): Promise<AuthTokenResponse> {
  const res = await fetchWithTimeout(
    `${API_BASE_URL}/auth/oauth2/login`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: 'google', credential }),
    },
    6000
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err.detail || 'Xác thực Google ID Token thất bại');
  }

  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  return data;
}

/**
 * Resolves current authenticated user profile.
 * - In Development: Fallback to mock/demo admin if backend is offline.
 * - In Production: Returns null if unauthenticated or on backend error.
 */
export async function getCurrentUser(): Promise<User | null> {
  const isDev = Boolean(import.meta.env.DEV);

  try {
    const token = getAuthToken();
    if (!token) {
      if (isDev) {
        // Auto-initiate default admin session in dev mode
        const defaultAuth = await loginDemo('admin@smartdesk.ai');
        return defaultAuth.user;
      }
      return null;
    }

    const headers = getAuthHeaders();
    const res = await fetchWithTimeout(`${API_BASE_URL}/auth/me`, { method: 'GET', headers }, 3000);
    if (!res.ok) {
      if (isDev) {
        // Token might be expired, fallback to demo admin in dev mode
        const defaultAuth = await loginDemo('admin@smartdesk.ai');
        return defaultAuth.user;
      }
      setAuthToken(null);
      return null;
    }

    const profile = await res.json();
    return {
      id: profile.id,
      email: profile.email,
      full_name: profile.full_name,
      role: profile.role,
      is_active: profile.is_active ?? true,
      workspace_id: profile.workspace_id ?? 1,
      avatar_url: profile.avatar_url,
      picture_url: profile.avatar_url,
    };
  } catch {
    if (isDev) {
      // Offline fallback mock user for local dev experience
      return {
        id: 1,
        email: 'admin@smartdesk.ai',
        full_name: 'SmartDesk Administrator',
        role: 'admin',
        is_active: true,
        workspace_id: 1,
        created_at: new Date().toISOString(),
      };
    }
    return null;
  }
}

export function logout(): void {
  setAuthToken(null);
}
