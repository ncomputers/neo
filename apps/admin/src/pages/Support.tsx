import { useState, useEffect } from 'react';

interface FaqEntry {
  title: string;
  content: string;
}

export function Support() {
  const [tab, setTab] = useState<'faq' | 'contact' | 'tickets' | 'feedback'>('faq');
  const [faqs, setFaqs] = useState<FaqEntry[]>([]);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    const files = import.meta.glob('../../../docs/faq/*.md', { as: 'raw' });
    const load = async () => {
      const entries: FaqEntry[] = [];
      for (const path in files) {
        const loader = files[path] as () => Promise<string>;
        const content = await loader();
        const title = content.split('\n')[0].replace(/^#\s*/, '') || path;
        entries.push({ title, content });
      }
      setFaqs(entries);
    };
    load();
  }, []);

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
            {faqs.length === 0 ? <p>Loading...</p> : <pre>{faqs[selected]?.content}</pre>}
          </div>
        </div>
      )}
      {tab === 'contact' && <p>Contact form coming soon.</p>}
      {tab === 'tickets' && <p>Tickets view coming soon.</p>}
      {tab === 'feedback' && <p>Feedback form coming soon.</p>}
    </div>
  );
}
