const TELEMETRY_BASE = (import.meta as any).env?.VITE_TELEMETRY_URL || '/telemetry';
const DISABLE_RUM = (import.meta as any).env?.VITE_DISABLE_RUM === 'true';

function post(path: string, data: unknown) {
  if (DISABLE_RUM) return;
  const body = JSON.stringify(data);
  try {
    const blob = new Blob([body], { type: 'application/json' });
    if (navigator.sendBeacon(`${TELEMETRY_BASE}${path}`, blob)) return;
  } catch {
    // ignore
  }
  fetch(`${TELEMETRY_BASE}${path}`, {
    method: 'POST',
    keepalive: true,
    headers: { 'Content-Type': 'application/json' },
    body,
  }).catch(() => {});
}

export function capturePageView(route: string) {
  const ttfb = (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.responseStart;
  try {
    const po = new PerformanceObserver((entryList) => {
      const entry = entryList.getEntries().at(-1) as LargestContentfulPaint | undefined;
      const lcp = entry?.startTime;
      po.disconnect();
      post('/pageview', { route, ttfb, lcp });
    });
    po.observe({ type: 'largest-contentful-paint', buffered: true });
  } catch {
    post('/pageview', { route, ttfb });
  }
}

export function captureError(err: Error, context?: Record<string, unknown>) {
  const { message, stack } = err;
  post('/error', { message, stack, context });
}
