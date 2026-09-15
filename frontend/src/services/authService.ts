/**
 * Authentication service — manages JWT storage, all /auth/* API calls,
 * and a global 401 interceptor that clears stale tokens.
 */

const baseDomain = ((import.meta as any).env?.VITE_API_BASE_URL as string)?.replace(/\/api$/, '') || '';
const AUTH_BASE = `${baseDomain}/auth`;
const TOKEN_KEY = 'eng_draw_token';
const USER_KEY  = 'eng_draw_user';

export interface AuthUser {
  user_id: number;
  email: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

// ─── Token storage ────────────────────────────────────────────────────────────

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as AuthUser; } catch { return null; }
}

function storeUser(user: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// ─── Authenticated fetch wrapper ──────────────────────────────────────────────

export async function authFetch(
  input: RequestInfo,
  init: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(init.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json';
  }

  const res = await fetch(input, { ...init, headers });

  // Global 401 handler — clear session so auth gate re-renders
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new CustomEvent('auth:expired', { detail: { message: 'Authentication required. Please log in to continue.' } }));
  }

  return res;
}

// ─── Auth API calls ───────────────────────────────────────────────────────────

export async function apiRegister(email: string, password: string): Promise<{ verification_token?: string }> {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Registration failed');
  return data;
}

export async function apiLogin(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Invalid email or password');
  setToken(data.access_token);
  storeUser(data.user);
  return data.user as AuthUser;
}

export async function apiGoogleLogin(idToken: string): Promise<AuthUser> {
  const res = await fetch(`${AUTH_BASE}/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Google sign-in failed');
  setToken(data.access_token);
  storeUser(data.user);
  return data.user as AuthUser;
}

export async function apiGetMe(): Promise<AuthUser> {
  const res = await authFetch(`${AUTH_BASE}/me`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Session expired');
  storeUser(data);
  return data as AuthUser;
}

export async function apiVerifyEmail(token: string): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Verification failed');
}

export async function apiResendVerification(email: string): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/resend-verification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d?.detail || 'Could not resend verification email');
  }
}

export async function apiRequestPasswordReset(email: string): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/request-password-reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d?.detail || 'Could not send reset email');
  }
}

export async function apiResetPassword(token: string, new_password: string): Promise<void> {
  const res = await fetch(`${AUTH_BASE}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Password reset failed');
}

export async function apiDeleteAccount(): Promise<void> {
  const res = await authFetch(`${AUTH_BASE}/me`, { method: 'DELETE' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || 'Account deletion failed');
  clearToken();
}

export function apiLogout(): void {
  clearToken();
}
