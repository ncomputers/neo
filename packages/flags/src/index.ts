import { useSyncExternalStore } from 'react';

let cache: Record<string, boolean> = {};
let etag: string | undefined;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function emit() {
  for (const l of Array.from(listeners)) l();
}

export function getFlag(name: string, defaultValue = false): boolean {
  return cache[name] ?? defaultValue;
}

export function useFlag(name: string, defaultValue = false): boolean {
  return useSyncExternalStore(subscribe, () => getFlag(name, defaultValue));
}

export async function refreshFlags(): Promise<Record<string, boolean>> {
  const res = await fetch('/admin/flags', {
    headers: etag ? { 'If-None-Match': etag } : undefined,
  });
  if (res.status === 304) {
    return cache;
  }
  if (!res.ok) {
    throw new Error(res.statusText);
  }
  const next = (await res.json()) as Record<string, boolean>;
  cache = next;
  etag = res.headers.get('ETag') || undefined;
  emit();
  return cache;
}
