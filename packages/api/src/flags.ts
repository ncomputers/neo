import { apiFetch } from './api';

let cache: Record<string, boolean> = {};

export async function loadFlags(): Promise<Record<string, boolean>> {
  cache = await apiFetch<Record<string, boolean>>('/admin/flags');
  return cache;
}

export function getFlag(name: string): boolean {
  return !!cache[name];
}

export function allFlags(): Record<string, boolean> {
  return { ...cache };
}

export async function setFlag(name: string, value: boolean): Promise<void> {
  cache[name] = value;
  await apiFetch(`/admin/flags/${name}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ value }),
  });
}

