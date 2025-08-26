import { apiFetch } from './api'

export function initRUM() {
  let consent = false
  try {
    const stored = localStorage.getItem('guestConsent')
    consent = stored ? JSON.parse(stored).analytics : false
  } catch (e) {
    consent = false
  }
  if (!consent) return

  const route = window.location.pathname
  const metrics = { route, consent: true }

  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const last = entries[entries.length - 1]
      if (last) metrics.lcp = (last.renderTime || last.loadTime) / 1000
    })
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true })
  } catch (e) {}

  try {
    let clsValue = 0
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) clsValue += entry.value
      }
      metrics.cls = clsValue
    })
    clsObserver.observe({ type: 'layout-shift', buffered: true })
  } catch (e) {}

  try {
    const inpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const dur = entry.duration / 1000
        metrics.inp = Math.max(metrics.inp || 0, dur)
      }
    })
    inpObserver.observe({ type: 'event', buffered: true })
  } catch (e) {}

  const nav = performance.getEntriesByType('navigation')[0]
  if (nav) metrics.ttfb = nav.responseStart / 1000

  const send = () => {
    apiFetch('/rum/vitals', {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metrics),
    })
  }

  addEventListener(
    'visibilitychange',
    () => {
      if (document.visibilityState === 'hidden') send()
    },
    { once: true },
  )
}
