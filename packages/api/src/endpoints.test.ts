import { describe, test, afterEach, expect } from 'vitest';
import { exportMenuI18n } from './endpoints';

afterEach(() => {
  // @ts-ignore
  delete globalThis.fetch;
});

describe('exportMenuI18n', () => {
  test('returns CSV with expected columns', async () => {
    const csv = 'id,en_name,hi_name\n';
    // @ts-ignore
    globalThis.fetch = async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(url).toBe('/menu/i18n/export?lang=en&lang=hi');
      expect(init).toEqual({ headers: {} });
      return new Response(csv, { status: 200 });
    };
    const res = await exportMenuI18n(['en', 'hi']);
    expect(res).toBe(csv);
  });
});
