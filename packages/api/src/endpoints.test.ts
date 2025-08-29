import { strict as assert } from 'node:assert';
import { test, afterEach } from 'node:test';
import { exportMenuI18n } from './endpoints';

afterEach(() => {
  // @ts-ignore
  delete globalThis.fetch;
});

test('exportMenuI18n returns CSV with expected columns', async () => {
  const csv = 'id,en_name,hi_name\n';
  // @ts-ignore
  globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
    assert.equal(url, '/menu/i18n/export?lang=en&lang=hi');
    assert.deepEqual(init, { headers: {} });
    return new Response(csv, { status: 200 });
  };
  const res = await exportMenuI18n(['en', 'hi']);
  assert.equal(res, csv);
});
