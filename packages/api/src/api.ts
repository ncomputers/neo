export interface FetchOptions extends RequestInit {
  idempotencyKey?: string;
  tenant?: string;
}

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { idempotencyKey, headers, ...rest } = opts;
  const h = new Headers(headers);
  if (idempotencyKey) h.set('Idempotency-Key', idempotencyKey);

  const res = await fetch(path, { ...rest, headers: h });
  const ct = res.headers.get('content-type');
  let data: unknown = null;
  if (ct && ct.includes('application/json')) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }
  if (!res.ok) {
    const message = (data as any)?.message || res.statusText;
    throw new Error(message);
  }
  return data as T;
}

export function idempotency() {
  return crypto.randomUUID();
}
