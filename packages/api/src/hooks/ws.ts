import { useEffect, useRef, useState } from 'react';

export interface WSOptions {
  protocols?: string[];
  onMessage?: (ev: MessageEvent) => void;
  onError?: (ev: Event) => void;
  onOpen?: (ev: Event) => void;
  heartbeatMs?: number;
  retryMs?: number;
}

export function useWS(url: string, opts?: WSOptions) {
  const { protocols, heartbeatMs = 30000, retryMs = 1000 } = opts ?? {};
  const onMessageRef = useRef<WSOptions['onMessage']>(opts?.onMessage);
  const onErrorRef = useRef<WSOptions['onError']>(opts?.onError);
  const onOpenRef = useRef<WSOptions['onOpen']>(opts?.onOpen);
  onMessageRef.current = opts?.onMessage;
  onErrorRef.current = opts?.onError;
  onOpenRef.current = opts?.onOpen;

  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const hbRef = useRef<ReturnType<typeof setInterval>>();

  const send = (msg: string | unknown) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
  };

  useEffect(() => {
    let stopped = false;
    let retry = 0;
    const connect = () => {
      const ws = new WebSocket(url, protocols);
      wsRef.current = ws;
      ws.onopen = (ev) => {
        setConnected(true);
        retry = 0;
        if (heartbeatMs) {
          hbRef.current && clearInterval(hbRef.current);
          hbRef.current = setInterval(() => {
            try {
              ws.send('ping');
            } catch {
              // ignore
            }
          }, heartbeatMs);
        }
        onOpenRef.current?.(ev);
      };
      ws.onmessage = (ev) => onMessageRef.current?.(ev);
      ws.onerror = (ev) => onErrorRef.current?.(ev);
      ws.onclose = () => {
        setConnected(false);
        if (hbRef.current) clearInterval(hbRef.current);
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
      if (hbRef.current) clearInterval(hbRef.current);
      wsRef.current?.close();
    };
  }, [url, protocols, heartbeatMs, retryMs]);

  return { send, connected };
}

