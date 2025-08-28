export interface FetchOptions extends RequestInit {
  idempotencyKey?: string;
  tenant?: string;
}

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { idempotencyKey, tenant, headers, ...rest } = opts;
  const h = new Headers(headers);
  const token = localStorage.getItem('token');
  if (token) h.set('Authorization', `Bearer ${token}`);
  if (tenant) h.set('X-Tenant', tenant);
  if (idempotencyKey) h.set('Idempotency-Key', idempotencyKey);
  const res = await fetch(path, { ...rest, headers: h });
  if (!res.ok) throw new Error(res.statusText);
  return res.json() as Promise<T>;
}

export function idempotency() {
  return crypto.randomUUID();
}
