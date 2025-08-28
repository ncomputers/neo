import { useCallback, useEffect, useState } from 'react';
import { apiFetch, useWS } from '@neo/api';
import { WS_BASE } from '../env';
import { PinModal } from '../components/PinModal';

interface Item {
  qty: number;
  name: string;
}

export type Status = 'NEW' | 'PREPARING' | 'READY' | 'PICKED';

interface Ticket {
  id: string;
  table: string;
  items: Item[];
  status: Status;
  age_s: number;
  promise_s: number;
}

export function Expo({ offlineMs = 10000 }: { offlineMs?: number } = {}) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [focused, setFocused] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [showPin, setShowPin] = useState(false);

  const fetchTickets = useCallback(async () => {
    try {
      const res = await apiFetch<{ tickets: Ticket[] }>('/kds/tickets');
      setTickets(res.tickets);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchTickets();
    const t = setInterval(fetchTickets, 5000);
    return () => clearInterval(t);
  }, [fetchTickets]);

  const { connected } = useWS(`${WS_BASE}/kds/tickets`, {
    onMessage: (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data) as { ticket: Ticket };
        setTickets((ts) => {
          const others = ts.filter((t) => t.id !== msg.ticket.id);
          return [...others, msg.ticket];
        });
      } catch {
        /* ignore */
      }
    },
  });

  useEffect(() => {
    let timer: NodeJS.Timeout | undefined;
    if (!connected) {
      timer = setTimeout(() => setOffline(true), offlineMs);
    } else {
      setOffline(false);
    }
    return () => timer && clearTimeout(timer);
  }, [connected]);

  const move = (id: string, status: Status) => {
    setTickets((ts) => ts.map((t) => (t.id === id ? { ...t, status } : t)));
  };

  const action = async (id: string, next: Status, endpoint: string) => {
    if (offline) return;
    if (!sessionStorage.getItem('token')) {
      setShowPin(true);
      return;
    }
    const prev = tickets.find((t) => t.id === id);
    if (!prev) return;
    move(id, next);
    try {
      await apiFetch(endpoint, { method: 'POST' });
    } catch {
      move(id, prev.status);
    }
  };

  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (!focused) return;
      const t = tickets.find((x) => x.id === focused);
      if (!t) return;
      if (e.key === 'a' || e.key === 'A') {
        if (t.status === 'NEW') action(t.id, 'PREPARING', `/kds/tickets/${t.id}/accept`);
      } else if (e.key === 'r' || e.key === 'R') {
        if (t.status === 'PREPARING') action(t.id, 'READY', `/kds/tickets/${t.id}/ready`);
      } else if (e.key === 'p' || e.key === 'P') {
        if (t.status === 'READY') action(t.id, 'PICKED', `/kds/tickets/${t.id}/picked`);
      } else if (e.key === 'z' || e.key === 'Z') {
        if (t.status === 'PICKED') action(t.id, 'READY', `/kds/tickets/${t.id}/undo`);
      }
    },
    [focused, tickets]
  );

  useEffect(() => {
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onKey]);

  const formatAge = (age_s: number) => {
    const m = Math.floor(age_s / 60);
    return `${m}m`;
  };
  const formatEta = (age_s: number, promise_s: number) => {
    const remaining = Math.max(0, promise_s - age_s);
    const m = Math.ceil(remaining / 60);
    return `${m}m`;
  };

  const columns: Status[] = ['NEW', 'PREPARING', 'READY', 'PICKED'];
  return (
    <div className="p-4 space-y-4">
      {offline && (
        <div data-testid="offline" className="bg-red-600 text-white p-2 text-center">
          Offline
        </div>
      )}
      <div className="grid grid-cols-4 gap-4">
        {columns.map((col) => (
          <div key={col}>
            <h3 className="font-semibold mb-2">{col.charAt(0) + col.slice(1).toLowerCase()}</h3>
            <ul className="space-y-2">
              {tickets
                .filter((t) => t.status === col)
                .map((t) => (
                  <li
                    key={t.id}
                    data-testid={`ticket-${t.id}`}
                    className={`border p-2 rounded cursor-pointer ${
                      focused === t.id ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => setFocused(t.id)}
                  >
                    <div className="flex justify-between">
                      <span>Table {t.table}</span>
                      <span className="text-sm" title={`ETA ${formatEta(t.age_s, t.promise_s)}`}>
                        {formatAge(t.age_s)}
                      </span>
                    </div>
                    <ul className="text-sm">
                      {t.items.map((i, idx) => (
                        <li key={idx}>
                          {i.qty}x{i.name}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
      {showPin && <PinModal open={showPin} onClose={() => setShowPin(false)} onSuccess={() => setShowPin(false)} />}
    </div>
  );
}

