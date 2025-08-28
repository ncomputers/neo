import { useCallback, useEffect, useState } from 'react';
import { apiFetch, useWS } from '@neo/api';
import { SkeletonList, EmptyState, Ticket as TicketIcon } from '@neo/ui';
import { useTranslation } from 'react-i18next';
import { WS_BASE, TENANT_ID } from '../env';
import { PinModal } from '../components/PinModal';
import { Snackbar } from '../components/Snackbar';

interface Ticket {
  order_id: number;
  table: string;
  age_s: number;
  allergen_badges: string[];
}

export function ExpoPage() {
  const [newTickets, setNewTickets] = useState<Ticket[]>([]);
  const [preparing, setPreparing] = useState<Ticket[]>([]);
  const [ready, setReady] = useState<Ticket[]>([]);
  const [picked, setPicked] = useState<Ticket[]>([]);
  const [offline, setOffline] = useState(!navigator.onLine);
  const [showPin, setShowPin] = useState(false);
  const [pending, setPending] = useState<(() => void) | null>(null);
  const [toast, setToast] = useState<{ msg: string; type?: 'success' | 'error' } | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useTranslation();

  const fetchTickets = useCallback(async () => {
    try {
      const headers = TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : undefined;
      const queue = await apiFetch<{ orders: { id: number; table_code: string; status: string }[] }>(
        '/kds/queue',
        { headers }
      );
      const expo = await apiFetch<{ orders: Ticket[] }>('/kds/expo', { headers });
      const nt: Ticket[] = [];
      const pt: Ticket[] = [];
      queue.orders.forEach((o) => {
        const base: Ticket = { order_id: o.id, table: o.table_code, age_s: 0, allergen_badges: [] };
        if (o.status === 'PLACED') nt.push(base);
        else if (o.status === 'IN_PROGRESS' || o.status === 'ACCEPTED') pt.push(base);
      });
      setNewTickets(nt);
      setPreparing(pt);
      setReady(expo.orders || []);
    } catch (err) {
      setToast({ msg: (err as Error).message, type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);
  useEffect(() => {
    const t = setInterval(fetchTickets, 5000);
    return () => clearInterval(t);
  }, [fetchTickets]);

  const { data: wsData } = useWS<{ orders: Ticket[] }>(`${WS_BASE}/kds/expo`);
  useEffect(() => {
    if (wsData?.orders) setReady(wsData.orders);
  }, [wsData]);

  useEffect(() => {
    const on = () => setOffline(!navigator.onLine);
    window.addEventListener('online', on);
    window.addEventListener('offline', on);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', on);
    };
  }, []);

  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const requireAuth = (fn: () => void) => {
    if (!localStorage.getItem('token')) {
      setPending(() => fn);
      setShowPin(true);
      return false;
    }
    return true;
  };

  const pick = async (t: Ticket) => {
    if (!requireAuth(() => pick(t))) return;
    try {
      await apiFetch(`/kds/expo/${t.order_id}/picked`, { method: 'POST', headers: TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : undefined });
      setReady((r) => r.filter((x) => x.order_id !== t.order_id));
      setPicked((p) => [...p, t]);
      setToast({ msg: 'Picked' });
    } catch (err) {
      setToast({ msg: (err as Error).message, type: 'error' });
    }
  };

  const accept = async (t: Ticket) => {
    if (!requireAuth(() => accept(t))) return;
    try {
      await apiFetch(`/kds/order/${t.order_id}/accept`, { method: 'POST', headers: TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : undefined });
      setNewTickets((n) => n.filter((x) => x.order_id !== t.order_id));
      setPreparing((p) => [...p, t]);
      setToast({ msg: 'Accepted' });
    } catch (err) {
      setToast({ msg: (err as Error).message, type: 'error' });
    }
  };

  const readyAction = async (t: Ticket) => {
    if (!requireAuth(() => readyAction(t))) return;
    try {
      await apiFetch(`/kds/order/${t.order_id}/ready`, { method: 'POST', headers: TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : undefined });
      setPreparing((p) => p.filter((x) => x.order_id !== t.order_id));
      setReady((r) => [...r, t]);
      setToast({ msg: 'Ready' });
    } catch (err) {
      setToast({ msg: (err as Error).message, type: 'error' });
    }
  };

  const undo = async (t: Ticket) => {
    if (!requireAuth(() => undo(t))) return;
    try {
      await apiFetch(`/kds/order/${t.order_id}/accept`, { method: 'POST', headers: TENANT_ID ? { 'X-Tenant-ID': TENANT_ID } : undefined });
      setPicked((p) => p.filter((x) => x.order_id !== t.order_id));
      setReady((r) => [...r, t]);
      setToast({ msg: 'Undo' });
    } catch (err) {
      setToast({ msg: (err as Error).message, type: 'error' });
    }
  };

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'P' || e.key === 'p') {
        const t = ready[0];
        if (t) pick(t);
      } else if (e.key === 'A' || e.key === 'a') {
        const t = newTickets[0];
        if (t) accept(t);
      } else if (e.key === 'R' || e.key === 'r') {
        const t = preparing[0];
        if (t) readyAction(t);
      } else if (e.key === 'Z' || e.key === 'z') {
        const t = picked[0];
        if (t) undo(t);
      }
    },
    [newTickets, preparing, ready, picked]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleKey]);

  const afterLogin = () => {
    if (pending) {
      const fn = pending;
      setPending(null);
      fn();
    }
  };

  const formatAge = (age_s: number) => {
    const m = Math.floor(age_s / 60);
    return `${m}m`;
  };
  const formatEta = (age_s: number) => {
    const remaining = Math.max(0, 300 - age_s);
    const m = Math.ceil(remaining / 60);
    return `${m}m`;
  };

  return (
    <div className="p-4 space-y-4">
      {offline && <div className="bg-red-600 text-white p-2 text-center">Offline</div>}
      <h2 className="text-xl font-bold">Expo</h2>
      {loading ? (
        <SkeletonList count={4} />
      ) : (
        <div className="grid grid-cols-4 gap-4">
          <div>
            <h3 className="font-semibold mb-2">New</h3>
            {newTickets.length === 0 ? (
              <EmptyState
                message={t('no_tickets')}
                icon={<TicketIcon className="w-12 h-12 mx-auto" />}
              />
            ) : (
              <ul className="space-y-2">
                {newTickets.map((t) => (
                  <li key={t.order_id} className="border p-2 rounded">
                    <div className="flex justify-between">
                      <span>Table {t.table}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="font-semibold mb-2">Preparing</h3>
            {preparing.length === 0 ? (
              <EmptyState
                message={t('no_tickets')}
                icon={<TicketIcon className="w-12 h-12 mx-auto" />}
              />
            ) : (
              <ul className="space-y-2">
                {preparing.map((t) => (
                  <li key={t.order_id} className="border p-2 rounded">
                    <div className="flex justify-between">
                      <span>Table {t.table}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="font-semibold mb-2">Ready</h3>
            {ready.length === 0 ? (
              <EmptyState
                message={t('no_tickets')}
                icon={<TicketIcon className="w-12 h-12 mx-auto" />}
              />
            ) : (
              <ul className="space-y-2">
                {ready.map((t) => (
                  <li key={t.order_id} className="border p-2 rounded">
                    <div className="flex justify-between">
                      <span>Table {t.table}</span>
                      <span className="text-sm text-gray-600" title={`ETA ${formatEta(t.age_s)}`}>
                        {formatAge(t.age_s)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h3 className="font-semibold mb-2">Picked</h3>
            {picked.length === 0 ? (
              <EmptyState
                message={t('no_tickets')}
                icon={<TicketIcon className="w-12 h-12 mx-auto" />}
              />
            ) : (
              <ul className="space-y-2">
                {picked.map((t) => (
                  <li key={t.order_id} className="border p-2 rounded text-gray-500">
                    <div className="flex justify-between">
                      <span>Table {t.table}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      {showPin && <PinModal open={showPin} onClose={() => setShowPin(false)} onSuccess={afterLogin} />}
      {toast && <Snackbar message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
