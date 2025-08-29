import { useState, useEffect } from 'react';

export function StaffSupport() {
  const [tickets, setTickets] = useState<any[]>([]);
  const [current, setCurrent] = useState<any | null>(null);
  const [status, setStatus] = useState('');
  const [tenant, setTenant] = useState('');
  const [date, setDate] = useState('');
  const [msg, setMsg] = useState('');
  const [internal, setInternal] = useState(false);
  const [canned, setCanned] = useState<any[]>([]);

  const load = () => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (tenant) params.set('tenant', tenant);
    if (date) params.set('date', date);
    fetch('/staff/support?' + params.toString())
      .then((r) => r.json())
      .then((r) => setTickets(r.data || []));
  };

  useEffect(() => { load(); }, [status, tenant, date]);

  const open = async (id: string) => {
    const r = await fetch(`/staff/support/${id}`);
    const d = await r.json();
    setCurrent(d.data);
  };

  const send = async () => {
    if (!current) return;
    await fetch(`/staff/support/${current.id}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, internal }),
    });
    setMsg('');
    open(current.id);
  };

  const close = async () => {
    if (!current) return;
    await fetch(`/staff/support/${current.id}/close`, { method: 'POST' });
    open(current.id);
  };

  const reopen = async () => {
    if (!current) return;
    await fetch(`/staff/support/${current.id}/reopen`, { method: 'POST' });
    open(current.id);
  };

  useEffect(() => {
    import('../../../docs/faq/meta.json').then((m) => setCanned(m.default));
  }, []);

  const insert = async (id: string) => {
    const files = import.meta.glob('../../../docs/faq/*.md', { as: 'raw' });
    const loader = files[`../../../docs/faq/${id}.md`];
    if (loader) {
      const content = await (loader as () => Promise<string>)();
      setMsg((m) => m + '\n' + content);
    }
  };

  return (
    <div className="flex">
      <div className="w-1/3">
        <input placeholder="status" value={status} onChange={(e) => setStatus(e.target.value)} />
        <input placeholder="tenant" value={tenant} onChange={(e) => setTenant(e.target.value)} />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button onClick={load}>Filter</button>
        <ul>
          {tickets.map((t) => (
            <li key={t.id}>
              <button onClick={() => open(t.id)}>{t.subject}</button>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex-1">
        {current && (
          <div>
            <h3>{current.subject}</h3>
            <button onClick={close}>Close</button>
            <button onClick={reopen}>Reopen</button>
            <ul>
              {current.messages.map((m: any) => (
                <li key={m.id}>
                  <b>{m.author}:</b> {m.body} {m.internal ? '(internal)' : ''}
                </li>
              ))}
            </ul>
            <select onChange={(e) => insert(e.target.value)} value="">
              <option value="">Canned reply</option>
              {canned.map((c: any) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
            <textarea value={msg} onChange={(e) => setMsg(e.target.value)} />
            <label>
              <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} /> internal
            </label>
            <button onClick={send}>Send</button>
          </div>
        )}
      </div>
    </div>
  );
}
