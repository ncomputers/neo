import { useEffect, useRef, useState } from 'react';

export interface SSEOptions {
  headers?: Record<string, string>;
  onMessage?: (ev: MessageEvent) => void;
  onError?: (ev: Event) => void;
  retryMs?: number;
}

export function useSSE(url: string, opts?: SSEOptions) {
  const { headers, retryMs = 1000 } = opts ?? {};
  const onMessageRef = useRef<SSEOptions['onMessage']>(opts?.onMessage);
  const onErrorRef = useRef<SSEOptions['onError']>(opts?.onError);
  onMessageRef.current = opts?.onMessage;
  onErrorRef.current = opts?.onError;
  const [connected, setConnected] = useState(false);
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let stopped = false;
    let retry = 0;
    const connect = () => {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore headers is non-standard but supported by polyfills
      const es: EventSource = new EventSource(url, { withCredentials: true, headers });
      esRef.current = es;
      es.onopen = () => {
        setConnected(true);
        retry = 0;
      };
      es.onmessage = (ev) => {
        setLastEventId(ev.lastEventId || null);
        onMessageRef.current?.(ev);
      };
      es.onerror = (ev) => {
        setConnected(false);
        onErrorRef.current?.(ev);
        es.close();
        if (!stopped) {
          const delay = Math.min(retryMs * 2 ** retry, 5000);
          retry++;
          setTimeout(connect, delay);
        }
      };
    };
    connect();
    return () => {
      stopped = true;
      esRef.current?.close();
    };
  }, [url, headers, retryMs]);

  return { connected, lastEventId };
}

