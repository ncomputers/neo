import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { apiFetch, idempotency } from './api';

test('apiFetch injects auth, tenant and idempotency headers', async () => {
  const calls: RequestInit[] = [];
  globalThis.localStorage = { getItem: () => 'secret-token' } as any;
  globalThis.fetch = async (_: RequestInfo | URL, init?: RequestInit) => {
    calls.push(init!);
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { 'content-type': 'application/json' }
    });
  };

  const res = await apiFetch<{ ok: boolean }>('/test', {
    tenant: 't1',
    idempotencyKey: 'abc'
  });
  assert.equal(res.ok, true);
  const h = new Headers(calls[0].headers);
  assert.equal(h.get('Authorization'), 'Bearer secret-token');
  assert.equal(h.get('X-Tenant'), 't1');
  assert.equal(h.get('Idempotency-Key'), 'abc');
});

test('apiFetch parses error json message', async () => {
  globalThis.localStorage = { getItem: () => null } as any;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ message: 'fail' }), {
      status: 400,
      headers: { 'content-type': 'application/json' }
    });
  await assert.rejects(() => apiFetch('/err'), /fail/);
});

test('idempotency generates uuid', () => {
  assert.match(idempotency(), /^[0-9a-f-]{36}$/i);
});
