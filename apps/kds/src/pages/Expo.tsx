import { useCallback, useEffect, useMemo, useState } from 'react';
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
  zone?: string;
}

export function Expo({ offlineMs = 10000 }: { offlineMs?: number } = {}) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [focused, setFocused] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [showPin, setShowPin] = useState(false);
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [zone, setZone] = useState<string | undefined>();
  const [order, setOrder] = useState<string[]>([]);

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
    setOrder((prev) => {
      const existing = prev.filter((id) => tickets.some((t) => t.id === id));
      const newIds = tickets.map((t) => t.id).filter((id) => !existing.includes(id));
      return [...existing, ...newIds];
    });
  }, [tickets]);

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

  const formatAge = (age_s: number) => {
    const m = Math.floor(age_s / 60);
    return `${m}m`;
  };
  const formatEta = (age_s: number, promise_s: number) => {
    const remaining = Math.max(0, promise_s - age_s);
    const m = Math.ceil(remaining / 60);
    return `${m}m`;
  };
  const allStatuses: Status[] = ['NEW', 'PREPARING', 'READY', 'PICKED'];
  const columns: Status[] = statusFilter === 'ALL' ? allStatuses : [statusFilter];
  const zones = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.zone).filter(Boolean))) as string[],
    [tickets]
  );
  const orderedTickets = useMemo(
    () => [...tickets].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)),
    [tickets, order]
  );
  const filteredTickets = useMemo(
    () =>
      orderedTickets.filter((t) => {
        const matchStatus = statusFilter === 'ALL' ? true : t.status === statusFilter;
        const q = searchQuery.toLowerCase();
        const matchSearch = q
          ? t.table.toLowerCase().includes(q) || t.items.some((i) => i.name.toLowerCase().includes(q))
          : true;
        const matchZone = zone ? t.zone === zone : true;
        return matchStatus && matchSearch && matchZone;
      }),
    [orderedTickets, statusFilter, searchQuery, zone]
  );
  const columnTickets = useMemo(() => {
    const map: Record<Status, Ticket[]> = { NEW: [], PREPARING: [], READY: [], PICKED: [] };
    filteredTickets.forEach((t) => {
      map[t.status].push(t);
    });
    return map;
  }, [filteredTickets]);
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
      } else if (e.key === 'ArrowDown') {
        const list = columnTickets[t.status];
        const idx = list.findIndex((x) => x.id === t.id);
        if (idx < list.length - 1) setFocused(list[idx + 1].id);
      } else if (e.key === 'ArrowUp') {
        const list = columnTickets[t.status];
        const idx = list.findIndex((x) => x.id === t.id);
        if (idx > 0) setFocused(list[idx - 1].id);
      } else if (e.key === 'ArrowRight') {
        const colIdx = columns.indexOf(t.status);
        if (colIdx >= 0 && colIdx < columns.length - 1) {
          const nextCol = columns[colIdx + 1];
          const idx = columnTickets[t.status].findIndex((x) => x.id === t.id);
          const dest = columnTickets[nextCol];
          if (dest.length) setFocused(dest[Math.min(idx, dest.length - 1)].id);
        }
      } else if (e.key === 'ArrowLeft') {
        const colIdx = columns.indexOf(t.status);
        if (colIdx > 0) {
          const prevCol = columns[colIdx - 1];
          const idx = columnTickets[t.status].findIndex((x) => x.id === t.id);
          const dest = columnTickets[prevCol];
          if (dest.length) setFocused(dest[Math.min(idx, dest.length - 1)].id);
        }
      } else if (e.key === 'Enter') {
        window.location.assign(`/kds/tickets/${t.id}`);
      }
    },
    [focused, tickets, columns, columnTickets]
  );

  useEffect(() => {
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onKey]);
  return (
    <div className="p-4 space-y-4">
      {offline && (
        <div data-testid="offline" className="bg-red-600 text-white p-2 text-center">
          Offline
        </div>
      )}
      <div className="flex space-x-2">
        {(['ALL', ...allStatuses] as const).map((s) => (
          <button
            key={s}
            className={`px-2 py-1 border rounded ${statusFilter === s ? 'bg-blue-500 text-white' : ''}`}
            onClick={() => setStatusFilter(s)}
          >
            {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
          </button>
        ))}
      </div>
      <div className="flex space-x-2">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search"
          className="border p-1 rounded"
        />
        {zones.length > 0 && (
          <select
            value={zone ?? ''}
            onChange={(e) => setZone(e.target.value || undefined)}
            className="border p-1 rounded"
          >
            <option value="">All Zones</option>
            {zones.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="grid grid-cols-4 gap-4">
        {columns.map((col) => (
          <div key={col}>
            <h3 className="font-semibold mb-2">{col.charAt(0) + col.slice(1).toLowerCase()}</h3>
            <ul className="space-y-2">
              {columnTickets[col].map((t) => (
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

