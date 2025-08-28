import { useEffect, useRef, useState } from 'react';

export function useSSE<T = unknown>(url: string, opts?: EventSourceInit) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Event | null>(null);
  const sourceRef = useRef<EventSource>();

  useEffect(() => {
    let retry = 0;
    let active = true;
    const connect = () => {
      const source = new EventSource(url, opts);
      sourceRef.current = source;
      source.onmessage = (e) => setData(JSON.parse(e.data));
      source.onerror = (e) => {
        setError(e);
        source.close();
        if (active) {
          retry++;
          setTimeout(connect, Math.min(1000 * 2 ** retry, 30000));
        }
      };
    };
    connect();
    return () => {
      active = false;
      sourceRef.current?.close();
    };
  }, [url]);

  return { data, error };
}
