import { useSyncExternalStore } from 'react';

let cache: Record<string, boolean> = {};
let etag: string | null = null;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit() {
  listeners.forEach((l) => l());
}

export function getFlag(name: string, def = false): boolean {
  return Object.prototype.hasOwnProperty.call(cache, name) ? cache[name] : def;
}

export function useFlag(name: string, def = false) {
  return useSyncExternalStore(subscribe, () => getFlag(name, def));
}

export async function refreshFlags(): Promise<Record<string, boolean>> {
  const headers: Record<string, string> = {};
  if (etag) headers['If-None-Match'] = etag;
  const res = await fetch('/admin/flags', { headers });
  if (res.status === 304) return cache;
  if (!res.ok) throw new Error(res.statusText);
  const data = (await res.json()) as Record<string, boolean>;
  cache = data;
  etag = res.headers.get('ETag');
  emit();
  return cache;
}
