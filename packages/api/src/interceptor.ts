import { getToken, refreshToken, clearToken } from './auth/pin';

export class AuthError extends Error {}

export function withInterceptors(fetchImpl = fetch) {
  return async function intercepted(input: RequestInfo | URL, init: RequestInit & { tenantId?: string; _retry?: boolean } = {}) {
    const { tenantId, _retry, headers, ...rest } = init;
    const h = new Headers(headers);
    const tokens = getToken();
    if (tokens?.accessToken) {
      h.set('Authorization', `Bearer ${tokens.accessToken}`);
    }
    if (tenantId) {
      h.set('X-Tenant-Id', tenantId);
    }
    h.set('X-Request-Id', crypto.randomUUID());
    const res = await fetchImpl(input, { ...rest, headers: h });
    if (res.status !== 401 || _retry) {
      return res;
    }
    const refreshed = await refreshToken();
    if (refreshed) {
      const retryHeaders = new Headers(headers);
      const t = getToken();
      if (t?.accessToken) {
        retryHeaders.set('Authorization', `Bearer ${t.accessToken}`);
      }
      if (tenantId) {
        retryHeaders.set('X-Tenant-Id', tenantId);
      }
      retryHeaders.set('X-Request-Id', crypto.randomUUID());
      return fetchImpl(input, { ...rest, headers: retryHeaders, _retry: true });
    }
    clearToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('unauthorized'));
      window.location.assign('/login');
    }
    throw new AuthError('Unauthorized');
  };
}

export type FetchWithInterceptor = ReturnType<typeof withInterceptors>;
