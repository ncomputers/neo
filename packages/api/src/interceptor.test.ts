import { describe, test, expect, vi } from 'vitest';
import { withInterceptors, AuthError } from './interceptor';
import * as pin from './auth/pin';

function response(status: number, body: any = '') {
  return new Response(body, { status });
}

describe('withInterceptors', () => {
  test('401 -> refresh once -> success', async () => {
    vi.spyOn(pin, 'getToken').mockReturnValue({ accessToken: 'a', refreshToken: 'r' });
    vi.spyOn(pin, 'refreshToken').mockResolvedValue(true);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(401))
      .mockResolvedValueOnce(response(200));
    const intercepted = withInterceptors(fetchMock as any);
    const res = await intercepted('/x');
    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  test('401 after refresh -> AuthError + redirect', async () => {
    vi.spyOn(pin, 'getToken').mockReturnValue({ accessToken: 'a', refreshToken: 'r' });
    vi.spyOn(pin, 'refreshToken').mockResolvedValue(false);
    const clearSpy = vi.spyOn(pin, 'clearToken').mockImplementation(() => {});
    const assignSpy = vi.fn();
    const dispatchSpy = vi.fn();
    (globalThis as any).window = { location: { assign: assignSpy }, dispatchEvent: dispatchSpy };
    const fetchMock = vi.fn().mockResolvedValue(response(401));
    const intercepted = withInterceptors(fetchMock as any);
    await expect(intercepted('/y')).rejects.toBeInstanceOf(AuthError);
    expect(clearSpy).toHaveBeenCalled();
    expect(dispatchSpy.mock.calls[0][0].type).toBe('unauthorized');
    expect(assignSpy).toHaveBeenCalledWith('/login');
  });
});
