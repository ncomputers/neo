import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { listAuditLogs, type AuditLog } from '@neo/api';

export function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [params, setParams] = useSearchParams();

  const actor = params.get('actor') || '';
  const event = params.get('event') || '';
  const date = params.get('date') || '';

  useEffect(() => {
    listAuditLogs({ actor, event, date })
      .then(setLogs)
      .catch(() => setLogs([]));
  }, [actor, event, date]);

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  function exportCsv() {
    const qs = new URLSearchParams(params);
    qs.set('format', 'csv');
    window.open(`/admin/audit?${qs.toString()}`);
  }

  return (
    <div>
      <div className="space-x-2 mb-4">
        <select value={actor} onChange={(e) => update('actor', e.target.value)}>
          <option value="">actor</option>
          <option value="staff">staff</option>
          <option value="system">system</option>
        </select>
        <select value={event} onChange={(e) => update('event', e.target.value)}>
          <option value="">event</option>
          <option value="order">order</option>
          <option value="kds">kds</option>
          <option value="billing">billing</option>
          <option value="support">support</option>
        </select>
        <input
          type="date"
          value={date}
          onChange={(e) => update('date', e.target.value)}
        />
        <button onClick={exportCsv}>Export CSV</button>
      </div>
      <table className="min-w-full">
        <thead>
          <tr>
            <th>Actor</th>
            <th>Event</th>
            <th>Entity</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td>{l.actor}</td>
              <td>{l.action}</td>
              <td>{l.entity}</td>
              <td>{new Date(l.created_at).toLocaleString()}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan={4}>No logs</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
