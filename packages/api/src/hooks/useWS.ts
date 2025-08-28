import { useEffect, useRef, useState } from 'react';

export interface WSOptions {
  protocols?: string | string[];
}

export function useWS<T = unknown>(url: string, opts?: WSOptions) {
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
          setTimeout(connect, Math.min(1000 * 2 ** retry, 30000));
        }
      };
    };
    connect();
    return () => {
      active = false;
      wsRef.current?.close();
    };
  }, [url, opts?.protocols]);

  const send = (msg: unknown) => wsRef.current?.send(JSON.stringify(msg));
  return { data, error, send };
}
