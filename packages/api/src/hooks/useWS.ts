import { useEffect, useRef, useState } from 'react';

export interface WSOptions {
  protocols?: string | string[];
  /**
   * Return delay in ms before the next reconnect attempt.
   * Receives retry count starting at 1.
   * Defaults to exponential backoff capped at 30s.
   */
  retryDelay?: (attempt: number) => number;
}

export function useWS<T = unknown>(url: string, opts?: WSOptions) {
  const delayFn = opts?.retryDelay ?? ((n: number) => Math.min(1000 * 2 ** n, 30000));
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Event | null>(null);
  const wsRef = useRef<WebSocket>();

  useEffect(() => {
    let retry = 0;
    let active = true;
    const connect = () => {
      const ws = new WebSocket(url, opts?.protocols);
      wsRef.current = ws;
      ws.onmessage = (e) => setData(JSON.parse(e.data));
      ws.onerror = (e) => setError(e);
      ws.onclose = () => {
        if (active) {
          retry++;
          setTimeout(connect, delayFn(retry));
        }
      };
    };
    connect();
    return () => {
      active = false;
      wsRef.current?.close();
    };
  }, [url, opts?.protocols, delayFn]);

  const send = (msg: unknown) => wsRef.current?.send(JSON.stringify(msg));
  return { data, error, send };
}
