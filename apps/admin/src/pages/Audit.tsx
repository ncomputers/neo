import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface Log {
  id: number;
  actor: string;
  action: string;
  entity: string;
  created_at: string;
}

export function Audit() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [params, setParams] = useSearchParams();
  const actor = params.get('actor') || '';
  const event = params.get('event') || '';
  const from = params.get('from') || '';
  const to = params.get('to') || '';

  useEffect(() => {
    const qs = new URLSearchParams();
    if (actor) qs.set('actor', actor);
    if (event) qs.set('event', event);
    if (from) qs.set('from', from);
    if (to) qs.set('to', to);
    fetch('/admin/audit?' + qs.toString())
      .then((r) => r.json())
      .then((r) => setLogs(r.data || []))
      .catch(() => {});
  }, [actor, event, from, to]);

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  const csvParams = new URLSearchParams();
  if (actor) csvParams.set('actor', actor);
  if (event) csvParams.set('event', event);
  if (from) csvParams.set('from', from);
  if (to) csvParams.set('to', to);
  csvParams.set('format', 'csv');
  const csvHref = '/admin/audit?' + csvParams.toString();

  return (
    <div>
      <div className="flex space-x-2" role="form">
        <select value={actor} onChange={(e) => updateParam('actor', e.target.value)}>
          <option value="">All actors</option>
          <option value="staff">staff</option>
          <option value="system">system</option>
        </select>
        <select value={event} onChange={(e) => updateParam('event', e.target.value)}>
          <option value="">All events</option>
          <option value="order">order</option>
          <option value="kds">kds</option>
          <option value="billing">billing</option>
          <option value="support">support</option>
        </select>
        <input type="date" value={from} onChange={(e) => updateParam('from', e.target.value)} />
        <input type="date" value={to} onChange={(e) => updateParam('to', e.target.value)} />
        <a href={csvHref} className="underline text-blue-600">
          Export CSV
        </a>
      </div>
      <table className="w-full mt-4">
        <thead>
          <tr>
            <th>When</th>
            <th>Actor</th>
            <th>Event</th>
            <th>Entity</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td>{new Date(l.created_at).toLocaleString()}</td>
              <td>{l.actor}</td>
              <td>{l.action}</td>
              <td>{l.entity}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan={4}>No entries</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
