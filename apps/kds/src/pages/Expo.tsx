import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch, useWS, useLicense } from '@neo/api';
import { WS_BASE } from '../env';
import { SettingsDrawer } from '../components/SettingsDrawer';
import { useKdsPrefs } from '../state/kdsPrefs';
import sounds from '../sounds.json';
import { Flag } from '@neo/ui';
import { getFlag } from '@neo/flags';

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
  const [statusFilter, setStatusFilter] = useState<Status | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [zone, setZone] = useState<string | undefined>();
  const [order, setOrder] = useState<string[]>([]);

  const { soundNew, soundReady, desktopNotify, darkMode, fontScale, printer, layout } =
    useKdsPrefs();
  const [showSettings, setShowSettings] = useState(false);
  const [fullscreen, setFullscreen] = useState(() => localStorage.getItem('kdsFullscreen') === '1');

  const prevTickets = useRef<Ticket[]>([]);
  const { data: license } = useLicense();
  const expired = license?.status === 'EXPIRED';

  const allStatuses: Status[] = ['NEW', 'PREPARING', 'READY', 'PICKED'];
  const columns: Status[] = statusFilter === 'ALL' ? allStatuses : [statusFilter];
  const zones = useMemo(
    () => Array.from(new Set(tickets.map((t) => t.zone).filter(Boolean))) as string[],
    [tickets]
  );
  const filteredTickets = useMemo(
    () =>
      tickets.filter((t) => {
        const matchStatus = statusFilter === 'ALL' ? true : t.status === statusFilter;
        const q = searchQuery.toLowerCase();
        const matchSearch = q
          ? t.table.toLowerCase().includes(q) || t.items.some((i) => i.name.toLowerCase().includes(q))
          : true;
        const matchZone = zone ? t.zone === zone : true;
        return matchStatus && matchSearch && matchZone;
      }),
    [tickets, statusFilter, searchQuery, zone]
  );

  const columnTickets = useMemo(() => {
    const map: Record<Status, Ticket[]> = {
      NEW: [],
      PREPARING: [],
      READY: [],
      PICKED: []
    };
    for (const t of filteredTickets) {
      map[t.status].push(t);
    }
    return map;
  }, [filteredTickets]);

  useEffect(() => {
    document.body.classList.toggle('dark', darkMode);
  }, [darkMode]);

  useEffect(() => {
    document.body.style.fontSize = `${fontScale}%`;
  }, [fontScale]);

  useEffect(() => {
    if (fullscreen && !document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => setFullscreen(false));
    } else if (!fullscreen && document.fullscreenElement) {
      document.exitFullscreen();
    }
    localStorage.setItem('kdsFullscreen', fullscreen ? '1' : '0');
  }, [fullscreen]);

  useEffect(() => {
    const handler = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

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
    for (const t of tickets) {
      const prev = prevTickets.current.find((p) => p.id === t.id);
      if (!prev && t.status === 'NEW') {
        if (soundNew) new Audio(sounds.new).play();
        if (
          desktopNotify &&
          typeof Notification !== 'undefined' &&
          Notification.permission === 'granted'
        ) {
          new Notification(`New order T-${t.table}`);
        }
      } else if (prev && prev.status !== 'READY' && t.status === 'READY') {
        if (soundReady) new Audio(sounds.ready).play();
        if (
          desktopNotify &&
          typeof Notification !== 'undefined' &&
          Notification.permission === 'granted'
        ) {
          new Notification(`Order ready T-${t.table}`);
        }
      }
    }
    prevTickets.current = tickets;
  }, [tickets, soundNew, soundReady, desktopNotify]);

  useEffect(() => {
    let timer: NodeJS.Timeout | undefined;
    if (!connected) {
      if (offlineMs === 0) {
        setOffline(true);
      } else {
        timer = setTimeout(() => setOffline(true), offlineMs);
      }
    } else {
      setOffline(false);
    }
    return () => timer && clearTimeout(timer);
  }, [connected, offlineMs]);

  const move = (id: string, status: Status) => {
    setTickets((ts) => ts.map((t) => (t.id === id ? { ...t, status } : t)));
  };

  const action = async (id: string, next: Status, endpoint: string) => {
    if (offline || expired) return;
    const prev = tickets.find((t) => t.id === id);
    if (!prev) return;
    move(id, next);
    try {
      await apiFetch(endpoint, { method: 'POST' });
    } catch {
      move(id, prev.status);
    }
  };

  const print = (id: string) => {
    if (!getFlag('kds_print')) return;
    apiFetch('/print/notify', {
      method: 'POST',
      body: JSON.stringify({ order_id: id, layout }),
      headers: { 'Content-Type': 'application/json' },
    }).catch(() => {
      /* ignore */
    });
    if (import.meta.env.MODE !== 'production') {
      console.log('stub print', { id, layout });
    }
  };

  const onKey = useCallback(
    (e: KeyboardEvent) => {
      const groups = columns.map((col) => filteredTickets.filter((t) => t.status === col));
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        if (!focused) {
          const first = groups[0]?.[0];
          if (first) setFocused(first.id);
          return;
        }
        const colIdx = groups.findIndex((g) => g.some((t) => t.id === focused));
        if (colIdx === -1) return;
        const rowIdx = groups[colIdx].findIndex((t) => t.id === focused);
        if (e.key === 'ArrowDown') {
          const nextRow = Math.min(rowIdx + 1, groups[colIdx].length - 1);
          setFocused(groups[colIdx][nextRow].id);
        } else if (e.key === 'ArrowUp') {
          const prevRow = Math.max(rowIdx - 1, 0);
          setFocused(groups[colIdx][prevRow].id);
        } else if (e.key === 'ArrowRight') {
          const nextCol = Math.min(colIdx + 1, groups.length - 1);
          const row = Math.min(rowIdx, groups[nextCol].length - 1);
          const target = groups[nextCol][row];
          if (target) setFocused(target.id);
        } else if (e.key === 'ArrowLeft') {
          const prevCol = Math.max(colIdx - 1, 0);
          const row = Math.min(rowIdx, groups[prevCol].length - 1);
          const target = groups[prevCol][row];
          if (target) setFocused(target.id);
        }
        e.preventDefault();
        return;
      }
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
      } else if (e.key === 'Enter') {
        window.location.assign(`/kds/tickets/${t.id}`);
      }
    },
    [columns, filteredTickets, focused, tickets]
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

  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only">
        Skip to content
      </a>
      <header
        className="p-4 dark:bg-gray-900 dark:text-white"
        style={{ fontSize: `${fontScale}%` }}
      >
        <div className="flex justify-end space-x-2">
          <button
            aria-label="Fullscreen"
            onClick={() => setFullscreen(!fullscreen)}
            className="border px-2 py-1 rounded"
          >
            {fullscreen ? '🡼' : '⛶'}
          </button>
          <button
            data-testid="settings-btn"
            aria-label="Settings"
            onClick={() => setShowSettings((s) => !s)}
            className="border px-2 py-1 rounded"
          >
            ⚙️
          </button>
        </div>
        {offline && (
          <div
            data-testid="offline"
            className="fixed top-2 right-2 bg-red-600 text-white px-2 py-1 rounded"
          >
            Offline
          </div>
        )}
      </header>
      <SettingsDrawer open={showSettings} onClose={() => setShowSettings(false)} />
      <main
        id="main"
        className="p-4 space-y-4 dark:bg-gray-900 dark:text-white"
        style={{ fontSize: `${fontScale}%` }}
      >
        <nav className="flex space-x-2" aria-label="Ticket status">
          {(['ALL', ...allStatuses] as const).map((s) => (
            <button
              key={s}
              className={`px-2 py-1 border rounded ${statusFilter === s ? 'bg-blue-500 text-white' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
            </button>
          ))}
        </nav>
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
                    {printer && (
                      <Flag name="kds_print">
                        <button
                          onClick={() => print(t.id)}
                          className="mt-2 border px-1 py-0.5 rounded text-sm"
                        >
                          Print KOT
                        </button>
                      </Flag>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}

