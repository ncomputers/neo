import { apiFetch } from '../api';

interface LoginPinRequest {
  pin: string;
  outletId?: string;
}
interface LoginPinResponse {
  accessToken: string;
  refreshToken: string;
  roles: string[];
}

interface Tokens {
  accessToken: string;
  refreshToken: string;
}

const memory: Partial<Tokens> = {};

export function setToken(tokens: Tokens) {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem('accessToken', tokens.accessToken);
    sessionStorage.setItem('refreshToken', tokens.refreshToken);
  } else {
    memory.accessToken = tokens.accessToken;
    memory.refreshToken = tokens.refreshToken;
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth'));
  }
}

export function getToken(): Tokens | null {
  if (typeof sessionStorage !== 'undefined') {
    const accessToken = sessionStorage.getItem('accessToken');
    const refreshToken = sessionStorage.getItem('refreshToken');
    if (accessToken && refreshToken) return { accessToken, refreshToken };
    return null;
  }
  if (memory.accessToken && memory.refreshToken) {
    return { accessToken: memory.accessToken, refreshToken: memory.refreshToken } as Tokens;
  }
  return null;
}

export function clearToken() {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem('accessToken');
    sessionStorage.removeItem('refreshToken');
  }
  memory.accessToken = undefined;
  memory.refreshToken = undefined;
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth'));
  }
}

export async function loginPin(body: LoginPinRequest): Promise<{ roles: string[] }> {
  const res = await apiFetch<LoginPinResponse>('/auth/pin', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' }
  });
  setToken({ accessToken: res.accessToken, refreshToken: res.refreshToken });
  return { roles: res.roles };
}

export async function refreshToken(): Promise<boolean> {
  const tokens = getToken();
  if (!tokens) return false;
  try {
    const res = await apiFetch<{ accessToken: string; refreshToken: string }>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken: tokens.refreshToken }),
      headers: { 'Content-Type': 'application/json' }
    });
    setToken({ accessToken: res.accessToken, refreshToken: res.refreshToken });
    return true;
  } catch {
    return false;
  }
}

export type FetchLike = typeof fetch;

export function addFetchInterceptors(fetchLike: FetchLike): FetchLike {
  return async (input: RequestInfo | URL, init: RequestInit & { tenant?: string; _retry?: boolean } = {}) => {
    const { tenant, _retry, headers, ...rest } = init;
    const h = new Headers(headers);
    const tokens = getToken();
    if (tokens?.accessToken) h.set('Authorization', `Bearer ${tokens.accessToken}`);
    if (tenant) h.set('X-Tenant', tenant);
    const res = await fetchLike(input, { ...rest, headers: h });
    if (res.status !== 401 || _retry) return res;
    const refreshed = await refreshToken();
    if (refreshed) {
      const retryHeaders = new Headers(headers);
      const t = getToken();
      if (t?.accessToken) retryHeaders.set('Authorization', `Bearer ${t.accessToken}`);
      if (tenant) retryHeaders.set('X-Tenant', tenant);
      return fetchLike(input, { ...rest, headers: retryHeaders, _retry: true } as any);
    }
    clearToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('unauthorized'));
      window.location.assign('/login');
    }
    return res;
  };
}
