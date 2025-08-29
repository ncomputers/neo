import { describe, expect, test, vi, beforeEach } from 'vitest';
import * as auth from './pin';
const { loginPin, getToken, setToken, clearToken, addFetchInterceptors } = auth;

function mockSession() {
  const store: Record<string, string> = {};
  (global as any).sessionStorage = {
    getItem: (k: string) => store[k] || null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
    clear: () => {
      for (const k of Object.keys(store)) delete store[k];
    }
  };
  return store;
}

describe('pin auth', () => {
  beforeEach(() => {
    mockSession();
    clearToken();
    vi.restoreAllMocks();
  });

  test('loginPin stores tokens', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ accessToken: 'a', refreshToken: 'r', roles: [] }),
        { status: 200, headers: { 'content-type': 'application/json' } }
      )
    );
    await loginPin({ pin: '1' });
    expect(getToken()).toEqual({ accessToken: 'a', refreshToken: 'r' });
  });

  test('interceptor adds Authorization header', async () => {
    setToken({ accessToken: 'abc', refreshToken: 'def' });
    const calls: RequestInit[] = [];
    const f = addFetchInterceptors(async (_: any, init?: RequestInit) => {
      calls.push(init!);
      return new Response(null, { status: 200 });
    });
    await f('/test');
    const h = new Headers(calls[0].headers);
    expect(h.get('Authorization')).toBe('Bearer abc');
  });

  test('401 triggers refresh', async () => {
    setToken({ accessToken: 'old', refreshToken: 'ref' });
    const fetchStub = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ accessToken: 'new', refreshToken: 'new' }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        )
      )
      .mockResolvedValue(new Response(null, { status: 200 }));
    global.fetch = fetchStub as any;
    const f = addFetchInterceptors(fetchStub as any);
    await f('/secure');
    expect(fetchStub).toHaveBeenCalledTimes(3);
    expect(getToken()).toEqual({ accessToken: 'new', refreshToken: 'new' });
  });
});
