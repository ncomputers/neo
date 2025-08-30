import { useState, useEffect, ChangeEvent } from 'react';

interface Ticket {
  id: string;
  subject: string;
  tenant: string;
  status: string;
  updated_at?: string;
}

interface Message {
  id: string;
  author: string;
  body: string;
  internal?: boolean;
  attachments?: string[];
}

interface Canned { id: string; title: string }

function toBase64(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.readAsDataURL(file);
  });
}

export function SupportStaff() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [current, setCurrent] = useState<any | null>(null);
  const [status, setStatus] = useState('');
  const [tenant, setTenant] = useState('');
  const [date, setDate] = useState('');
  const [msg, setMsg] = useState('');
  const [internal, setInternal] = useState(false);
  const [attachments, setAttachments] = useState<string[]>([]);
  const [canned, setCanned] = useState<Canned[]>([]);

  const load = () => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (tenant) params.set('tenant', tenant);
    if (date) params.set('date', date);
    fetch('/staff/support?' + params.toString())
      .then((r) => r.json())
      .then((r) => setTickets(r.data || []));
  };

  useEffect(() => {
    load();
  }, [status, tenant, date]);

  const open = async (id: string) => {
    const r = await fetch(`/staff/support/${id}`);
    const d = await r.json();
    setCurrent(d.data);
  };

  const send = async () => {
    if (!current) return;
    const payload = { message: msg, internal, attachments };
    setCurrent({
      ...current,
      messages: [
        ...current.messages,
        { id: 'tmp', author: 'agent', body: msg, internal, attachments },
      ],
    });
    setMsg('');
    setAttachments([]);
    await fetch(`/staff/support/${current.id}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
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
    import('../../../../docs/faq/meta.json').then((m) => setCanned(m.default));
  }, []);

  const insert = (id: string) => {
    const entry = canned.find((c) => c.id === id);
    if (entry) setMsg((m) => m + '\n' + entry.title);
  };

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files).slice(0, 3) : [];
    const out: string[] = [];
    for (const f of files) out.push(await toBase64(f));
    setAttachments(out);
  };

  return (
    <div className="flex">
      <div className="flex-1">
        <div className="flex space-x-2 mb-2">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">status</option>
            <option value="open">OPEN</option>
            <option value="pending">PENDING</option>
            <option value="resolved">RESOLVED</option>
          </select>
          <input
            placeholder="tenant"
            value={tenant}
            onChange={(e) => setTenant(e.target.value)}
          />
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button onClick={load}>Filter</button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th>ID</th>
              <th>Subject</th>
              <th>Tenant</th>
              <th>Status</th>
              <th>Last Update</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.id}>
                <td>
                  <button onClick={() => open(t.id)}>{t.id.slice(0, 8)}</button>
                </td>
                <td>{t.subject}</td>
                <td>{t.tenant}</td>
                <td>{t.status}</td>
                <td>{t.updated_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="w-48 border-l pl-2">
        <h4>Canned</h4>
        <ul>
          {canned.map((c) => (
            <li key={c.id}>
              <button onClick={() => insert(c.id)}>{c.title}</button>
            </li>
          ))}
        </ul>
      </div>
      {current && (
        <div className="fixed top-0 right-0 w-1/3 h-full bg-white border-l p-4 overflow-y-auto">
          <h3>{current.subject}</h3>
          <p className="text-sm mb-2">
            {current.tenant} – {current.status}
          </p>
          <button onClick={close}>Close</button>
          <button onClick={reopen}>Reopen</button>
          <ul className="my-2 space-y-1">
            {current.messages.map((m: Message) => (
              <li key={m.id}>
                <b>{m.author}:</b> {m.body}{' '}
                {m.internal ? '(internal)' : ''}
              </li>
            ))}
          </ul>
          <textarea
            className="w-full border"
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
          />
          <div className="my-1">
            <label>
              <input
                type="checkbox"
                checked={internal}
                onChange={(e) => setInternal(e.target.checked)}
              />
              internal
            </label>
          </div>
          <input type="file" multiple accept="image/*" onChange={onFile} />
          <button onClick={send}>Send</button>
        </div>
      )}
    </div>
  );
}
