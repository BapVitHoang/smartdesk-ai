/**
 * HTTP Client, Error Handling, and Authentication State for SmartDesk AI
 */

import { ToastType } from '../../types';

// 1. Base URL Configuration
export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';

// 2. Global Toast Notifier for graceful fallback warnings
export type ToastNotifier = (msg: string, type?: ToastType) => void;
let globalToastNotifier: ToastNotifier | null = null;

export function registerApiToastHandler(fn: ToastNotifier | null): void {
  globalToastNotifier = fn;
}

export function notifyFallback(msg: string, type: ToastType = 'warning'): void {
  if (globalToastNotifier) {
    globalToastNotifier(msg, type);
  }
}

// 3. API Error Definition
export class ApiError extends Error {
  statusCode: number;
  detail: string;

  constructor(statusCode: number, detail: string) {
    super(detail || `HTTP ${statusCode}`);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

export function isNetworkError(error: any): boolean {
  return (
    error instanceof TypeError ||
    error?.name === 'AbortError' ||
    (typeof error?.message === 'string' &&
      (error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError') ||
        error.message.includes('aborted') ||
        error.message.includes('fetch failed')))
  );
}

// 4. Token & Auth Storage
const AUTH_TOKEN_KEY = 'smartdesk_access_token';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {
    // Ignore localStorage errors in private browsing
  }
}

export function getAuthHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = {
    ...customHeaders,
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// 5. Mock Mode Switch Check
export function isMockEnabled(): boolean {
  return (import.meta as any).env?.VITE_USE_MOCKS === 'true';
}

// 6. Fetch With Timeout Helper
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 5000
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  
  // Merge auth headers if available
  const existingHeaders = (options.headers || {}) as Record<string, string>;
  const mergedHeaders = getAuthHeaders(existingHeaders);

  try {
    const res = await fetch(url, {
      ...options,
      headers: mergedHeaders,
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}
