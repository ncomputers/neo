import { useState, useEffect } from 'react';
import { collectDiagnostics } from '../diagnostics';

interface FaqEntry {
  title: string;
  content: string;
}

export function Support() {
  const [tab, setTab] = useState<'faq' | 'contact' | 'tickets' | 'feedback'>('faq');
  const [faqs, setFaqs] = useState<FaqEntry[]>([]);
  const [selected, setSelected] = useState(0);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [channel, setChannel] = useState<'email' | 'whatsapp'>('email');
  const [includeDiag, setIncludeDiag] = useState(false);
  const [tickets, setTickets] = useState<any[]>([]);
  const [current, setCurrent] = useState<any | null>(null);
  const [reply, setReply] = useState('');
  const [score, setScore] = useState(0);
  const [comment, setComment] = useState('');
  const [thanks, setThanks] = useState(false);

  useEffect(() => {
    const load = async () => {
      const meta = await import('../../../../docs/faq/meta.json');
      const entries: FaqEntry[] = [];
      for (const item of meta.default) {
        const md = await import(`../../../../docs/faq/${item.id}.md?raw`);
        entries.push({ title: item.title, content: md.default });
      }
      setFaqs(entries);
    };
    load();
  }, []);

  useEffect(() => {
    if (tab === 'tickets') {
      fetch('/support/tickets')
        .then((r) => r.json())
        .then((r) => setTickets(r.data || []));
    }
  }, [tab]);

  const submitTicket = async () => {
    const payload: any = { subject, message, channel, attachments: [] };
    if (includeDiag) payload.includeDiagnostics = true, payload.diagnostics = collectDiagnostics(window.location.pathname);
    await fetch('/support/tickets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setSubject('');
    setMessage('');
    setIncludeDiag(false);
    setTab('tickets');
  };

  const openTicket = async (id: string) => {
    const r = await fetch(`/support/tickets/${id}`);
    const data = await r.json();
    setCurrent(data.data);
  };

  const sendReply = async () => {
    if (!current) return;
    await fetch(`/support/tickets/${current.id}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: reply }),
    });
    setReply('');
    openTicket(current.id);
  };

  const submitFeedback = async () => {
    await fetch('/support/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score, comment }),
    });
    setThanks(true);
  };

  return (
    <div>
      <div className="flex space-x-2 mb-4" role="tablist">
        {(['faq', 'contact', 'tickets', 'feedback'] as const).map((t) => (
          <button
            key={t}
            role="tab"
            className={tab === t ? 'font-bold' : ''}
            onClick={() => setTab(t)}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>
      {tab === 'faq' && (
        <div className="flex">
          <ul className="w-48 mr-4">
            {faqs.map((f, idx) => (
              <li key={idx}>
                <button onClick={() => setSelected(idx)}>{f.title}</button>
              </li>
            ))}
            {faqs.length === 0 && <li>No FAQs</li>}
          </ul>
          <div className="flex-1 border-l pl-4">
            {faqs.length === 0 ? (
              <p>Loading...</p>
            ) : (
              <div
                dangerouslySetInnerHTML={{
                  __html: faqs[selected]?.content
                    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                    .replace(/\n/g, '<br/>'),
                }}
              />
            )}
          </div>
        </div>
      )}
      {tab === 'contact' && (
        <div className="space-y-2">
          <input
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <textarea
            placeholder="Message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <select value={channel} onChange={(e) => setChannel(e.target.value as any)}>
            <option value="email">email</option>
            <option value="whatsapp">whatsapp</option>
          </select>
          <label>
            <input
              type="checkbox"
              checked={includeDiag}
              onChange={(e) => setIncludeDiag(e.target.checked)}
            />
            Include diagnostics
          </label>
          <button onClick={submitTicket}>Submit</button>
        </div>
      )}
      {tab === 'tickets' && (
        <div className="flex">
          <ul className="w-48 mr-4">
            {tickets.map((t) => (
              <li key={t.id}>
                <button onClick={() => openTicket(t.id)}>{t.subject}</button>
              </li>
            ))}
            {tickets.length === 0 && <li>No tickets</li>}
          </ul>
          <div className="flex-1">
            {current ? (
              <div>
                <h3>{current.subject}</h3>
                <ul>
                  {current.messages.map((m: any) => (
                    <li key={m.id}>
                      <b>{m.author}:</b> {m.body}
                    </li>
                  ))}
                </ul>
                <textarea
                  placeholder="Reply"
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                />
                <button onClick={sendReply}>Send</button>
              </div>
            ) : (
              <p>Select a ticket</p>
            )}
          </div>
        </div>
      )}
      {tab === 'feedback' && (
        <div className="space-y-2">
          {thanks ? (
            <p>Thanks!</p>
          ) : (
            <>
              <input
                type="number"
                min={0}
                max={10}
                value={score}
                onChange={(e) => setScore(parseInt(e.target.value))}
              />
              <textarea
                placeholder="Comment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <button onClick={submitFeedback}>Submit</button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
