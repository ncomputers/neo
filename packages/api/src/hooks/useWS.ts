import { useEffect, useRef, useState } from 'react';

export function useWS<T = unknown>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Event | null>(null);
  const wsRef = useRef<WebSocket>();

  useEffect(() => {
    let retry = 0;
    let active = true;
    const connect = () => {
      const ws = new WebSocket(url);
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
  }, [url]);

  const send = (msg: unknown) => wsRef.current?.send(JSON.stringify(msg));
  return { data, error, send };
}
