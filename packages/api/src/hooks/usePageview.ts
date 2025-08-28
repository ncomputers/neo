import { useEffect } from 'react';
import { apiFetch } from '../api';

/**
 * Report client-side page views to the backend.
 * Debounces rapid navigation to avoid spamming the endpoint.
 */
export function usePageview(path: string, delay = 500) {
  useEffect(() => {
    if (!path) return;
    const t = setTimeout(() => {
      void apiFetch('/telemetry/pageview', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ path })
      }).catch(() => {});
    }, delay);
    return () => clearTimeout(t);
  }, [path, delay]);
}
