import test from 'node:test'
import assert from 'node:assert/strict'
import { bgSyncPost } from '../../static/js/bg_sync.js'

test('offline enqueue queues request', async () => {
  const messages = []
  Object.defineProperty(global, 'navigator', {
    value: {
      onLine: false,
      serviceWorker: {
        ready: Promise.resolve({
          active: { postMessage: m => messages.push(m) },
          sync: { register: tag => messages.push({ tag }) },
        }),
      },
    },
    configurable: true,
  })
  global.fetch = () => {
    throw new Error('should not fetch offline')
  }
  const res = await bgSyncPost('/api/test', { body: { a: 1 } })
  assert.equal(res.queued, true)
  assert.ok(res.key)
  assert.equal(messages[0].type, 'BG_SYNC_ENQUEUE')
  assert.equal(messages[1].tag, 'api-queue')
})

test('online fetch bypasses queue', async () => {
  let called = false
  Object.defineProperty(global, 'navigator', {
    value: { onLine: true, serviceWorker: { ready: Promise.resolve({}) } },
    configurable: true,
  })
  global.fetch = async (url, opts) => {
    called = true
    assert(opts.headers.get('Idempotency-Key'))
    return { ok: true }
  }
  await bgSyncPost('/api/test', { body: { a: 1 } })
  assert(called)
})
