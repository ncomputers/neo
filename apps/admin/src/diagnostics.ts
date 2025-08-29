const logs: string[] = [];
(['log', 'warn', 'error'] as const).forEach((level) => {
  const orig = console[level];
  console[level] = (...args: any[]) => {
    logs.push(args.join(' '));
    if (logs.length > 20) logs.shift();
    orig(...args);
  };
});

interface ApiErr { path: string; status: number }
const apiErrors: ApiErr[] = [];
const origFetch = window.fetch;
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const res = await origFetch(input, init);
  if (!res.ok) {
    const url = typeof input === 'string' ? input : (input as any).url;
    apiErrors.push({ path: url, status: res.status });
    if (apiErrors.length > 10) apiErrors.shift();
  }
  return res;
};

const secretRe = /(?:bearer|token|authorization|utr|upi|card)/gi;

function redact(data: any): any {
  if (typeof data === 'string') return data.replace(secretRe, '****');
  if (Array.isArray(data)) return data.map(redact);
  if (data && typeof data === 'object') {
    const out: any = {};
    for (const k in data) out[k] = redact(data[k]);
    return out;
  }
  return data;
}

export function collectDiagnostics(route: string) {
  return redact({
    app: 'admin',
    appVersion: (import.meta as any).env.VITE_APP_VERSION || 'dev',
    userAgent: navigator.userAgent,
    route,
    logs: [...logs],
    errors: [...apiErrors],
  });
}
