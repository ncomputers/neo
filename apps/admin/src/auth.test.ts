import { describe, test, expect, beforeEach, vi } from 'vitest';
import { useAuth } from './auth';

function createToken() {
  const payload = { roles: ['owner'], tenants: [], a: String.fromCharCode(190), b: String.fromCharCode(191) };
  const base64 = Buffer.from(JSON.stringify(payload))
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
  return `aaa.${base64}.bbb`;
}

describe('auth', () => {
  beforeEach(() => {
    useAuth.setState({ token: null, roles: [], tenants: [], tenantId: null });
    sessionStorage.clear();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  test('decodes base64url tokens', async () => {
    const token = createToken();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token })
    }) as any);
    await useAuth.getState().login('1234');
    expect(useAuth.getState().roles).toEqual(['owner']);
  });

  test('logout removes tenantId', () => {
    localStorage.setItem('tenantId', '1');
    sessionStorage.setItem('token', 't');
    useAuth.setState({ token: 't', roles: ['owner'], tenants: [], tenantId: '1' });
    useAuth.getState().logout();
    expect(localStorage.getItem('tenantId')).toBeNull();
    expect(sessionStorage.getItem('token')).toBeNull();
  });
});
