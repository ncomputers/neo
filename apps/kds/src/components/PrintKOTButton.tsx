import { apiFetch } from '@neo/api';
import { useKdsPrefs } from '../state/kdsPrefs';

interface Item {
  qty: number;
  name: string;
}

interface Ticket {
  id: string;
  table: string;
  items: Item[];
}

export function PrintKOTButton({ ticket }: { ticket: Ticket }) {
  const { printer, layout, set } = useKdsPrefs();

  if (!printer) return null;

  const print = (l: 'compact' | 'full') => {
    apiFetch('/print/notify', {
      method: 'POST',
      body: JSON.stringify({ order_id: ticket.id, layout: l }),
      headers: { 'Content-Type': 'application/json' },
    }).catch(() => {
      /* ignore */
    });
    if (import.meta.env.MODE !== 'production') {
      const w = window.open('', '_blank');
      if (w) {
        const items = ticket.items
          .map((i) => `<li>${i.qty}x ${i.name}</li>`)
          .join('');
        w.document.write(
          `<html><body><h1>Table ${ticket.table}</h1><ul>${items}</ul></body></html>`
        );
        w.document.close();
        w.focus();
        w.print();
      }
    }
  };

  return (
    <div className="mt-2 flex items-center space-x-1">
      <button
        onClick={() => print(layout)}
        className="border px-1 py-0.5 rounded text-sm"
      >
        Print KOT
      </button>
      <select
        value={layout}
        onChange={(e) => set({ layout: e.target.value as 'compact' | 'full' })}
        className="border p-1 rounded text-sm"
      >
        <option value="compact">Compact</option>
        <option value="full">Full</option>
      </select>
    </div>
  );
}

