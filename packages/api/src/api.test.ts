import { describe, expect, test } from 'vitest';
import { apiFetch, idempotency } from './api';
import { addFetchInterceptors } from './auth/pin';

describe('apiFetch', () => {
  test('passes through tenant and idempotency', async () => {
    const calls: RequestInit[] = [];
    const fetchStub = async (_: RequestInfo | URL, init?: RequestInit) => {
      calls.push(init!);
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' }
      });
    };
    globalThis.fetch = addFetchInterceptors(fetchStub as any);

    const res = await apiFetch<{ ok: boolean }>('/test', {
      tenant: 't1',
      idempotencyKey: 'abc'
    });
    expect(res.ok).toBe(true);
    const h = new Headers(calls[0].headers);
    expect(h.get('X-Tenant')).toBe('t1');
    expect(h.get('Idempotency-Key')).toBe('abc');
  });

  test('parses error json message', async () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ message: 'fail' }), {
        status: 400,
        headers: { 'content-type': 'application/json' }
      });
    await expect(apiFetch('/err')).rejects.toThrow(/fail/);
  });

  test('idempotency generates uuid', () => {
    expect(idempotency()).toMatch(/^[0-9a-f-]{36}$/i);
  });
});
