import { useEffect, useRef, useState } from 'react';

export interface SSEOptions extends EventSourceInit {
  /**
   * Return delay in ms before the next reconnect attempt.
   * Receives retry count starting at 1.
   * Defaults to exponential backoff capped at 30s.
   */
  retryDelay?: (attempt: number) => number;
}

export function useSSE<T = unknown>(url: string, opts?: SSEOptions) {
  const { retryDelay, ...esOpts } = opts ?? {};
  const delayFn = retryDelay ?? ((n: number) => Math.min(1000 * 2 ** n, 30000));
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Event | null>(null);
  const sourceRef = useRef<EventSource>();

  useEffect(() => {
    let retry = 0;
    let active = true;
    const connect = () => {
      const source = new EventSource(url, esOpts);
      sourceRef.current = source;
      source.onmessage = (e) => setData(JSON.parse(e.data));
      source.onerror = (e) => {
        setError(e);
        source.close();
        if (active) {
          retry++;
          setTimeout(connect, delayFn(retry));
        }
      };
    };
    connect();
    return () => {
      active = false;
      sourceRef.current?.close();
    };
  }, [url, esOpts, delayFn]);

  return { data, error };
}
