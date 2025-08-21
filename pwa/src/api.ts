const API_BASE = import.meta.env.VITE_API_BASE || ''
const TENANT_ID = import.meta.env.VITE_TENANT_ID || ''

export async function apiFetch(path: string, options: RequestInit = {}) {
  const url = API_BASE ? `${API_BASE}${path}` : path
  const headers = {
    ...(options.headers || {}),
    ...(TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : {}),
  }
  return fetch(url, { ...options, headers })
}
