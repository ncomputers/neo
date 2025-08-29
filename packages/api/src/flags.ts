import { apiFetch } from './api';

export async function setFlag(name: string, value: boolean): Promise<void> {
  await apiFetch(`/admin/flags/${name}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ value }),
  });
}
