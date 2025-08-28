const TELEMETRY_BASE = (import.meta as any).env?.VITE_TELEMETRY_URL || '/telemetry';
const DISABLE_RUM = (import.meta as any).env?.VITE_DISABLE_RUM === '1';

function post(path: string, data: unknown) {
  if (DISABLE_RUM) return;
  try {
    const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    navigator.sendBeacon(`${TELEMETRY_BASE}${path}`, blob);
  } catch {
    // ignore
  }
}

export function capturePageView(route: string) {
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
  const ttfb = nav ? nav.responseStart - nav.requestStart : undefined;
  const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
  const lcp = lcpEntries.length ? lcpEntries[lcpEntries.length - 1].startTime : undefined;
  post('/pageview', { route, ttfb, lcp });
}

export function captureError(err: unknown, context?: Record<string, unknown>) {
  const message = err instanceof Error ? err.message : String(err);
  const stack = err instanceof Error ? err.stack : undefined;
  post('/error', { message, stack, context });
}
