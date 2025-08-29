import { useState, useEffect } from 'react';

interface Log {
  id: number;
  actor: string;
  action: string;
  entity: string;
  created_at: string;
}

export function Audit() {
  const [actor, setActor] = useState('');
  const [event, setEvent] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [logs, setLogs] = useState<Log[]>([]);

  const load = async () => {
    const params = new URLSearchParams();
    if (actor) params.set('actor', actor);
    if (event) params.set('event', event);
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    const res = await fetch(`/admin/audit?${params.toString()}`);
    const data = await res.json();
    setLogs(data.data || []);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const csvHref = () => {
    const params = new URLSearchParams();
    if (actor) params.set('actor', actor);
    if (event) params.set('event', event);
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    params.set('format', 'csv');
    return `/admin/audit?${params.toString()}`;
  };

  return (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <select value={actor} onChange={(e) => setActor(e.target.value)}>
          <option value="">actor</option>
          <option value="staff">staff</option>
          <option value="system">system</option>
        </select>
        <select value={event} onChange={(e) => setEvent(e.target.value)}>
          <option value="">event</option>
          <option value="order">order</option>
          <option value="kds">kds</option>
          <option value="billing">billing</option>
          <option value="support">support</option>
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        <button onClick={load}>Filter</button>
        <a href={csvHref()} className="btn">Export CSV</a>
      </div>
      <table className="min-w-full border">
        <thead>
          <tr>
            <th>ID</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Entity</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td>{l.id}</td>
              <td>{l.actor}</td>
              <td>{l.action}</td>
              <td>{l.entity}</td>
              <td>{new Date(l.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Audit;
