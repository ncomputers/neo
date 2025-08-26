import { onCLS, onINP, onLCP } from 'web-vitals'

export function initRUM(ctx) {
  let consent = false
  try {
    const stored = localStorage.getItem('guestConsent')
    consent = stored ? JSON.parse(stored).analytics : false
  } catch (e) {
    consent = false
  }
  if (!consent) return

  const send = (metric) => {
    const body = {
      ctx,
      consent: true,
    }
    if (metric.name === 'CLS') body.cls = metric.value
    else if (metric.name === 'LCP') body.lcp = metric.value / 1000
    else if (metric.name === 'INP') body.inp = metric.value / 1000

    fetch('/rum/vitals', {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  onLCP(send)
  onCLS(send)
  onINP(send)
}
