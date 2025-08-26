export async function bgSyncPost(url, options = {}) {
  const headers = new Headers(options.headers || {})
  if (!headers.has('content-type')) {
    headers.set('content-type', 'application/json')
  }
  const key =
    headers.get('Idempotency-Key') ||
    (globalThis.crypto?.randomUUID
      ? globalThis.crypto.randomUUID()
      : Math.random().toString(36).slice(2))
  headers.set('Idempotency-Key', key)
  const body =
    typeof options.body === 'string'
      ? options.body
      : JSON.stringify(options.body || {})
  if (navigator.onLine) {
    return fetch(url, { method: 'POST', headers, body })
  }
  const reg = await navigator.serviceWorker.ready
  reg.active?.postMessage({
    type: 'BG_SYNC_ENQUEUE',
    req: {
      key,
      url,
      method: 'POST',
      headers: Array.from(headers.entries()),
      body,
    },
  })
  await reg.sync.register('api-queue')
  return { queued: true, key }
}

if (typeof window !== 'undefined') {
  window.bgSyncPost = bgSyncPost
}
