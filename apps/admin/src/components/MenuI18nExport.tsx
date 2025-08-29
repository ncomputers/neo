import { useState } from 'react';
import { Button, toast } from '@neo/ui';

const LANGS = ['en', 'hi'];

interface Props {
  tenant: string;
}

export function MenuI18nExport({ tenant }: Props) {
  const [langs, setLangs] = useState<string[]>([]);

  const toggleLang = (l: string) => {
    setLangs((prev) =>
      prev.includes(l) ? prev.filter((x) => x !== l) : [...prev, l]
    );
  };

  const doExport = async () => {
    if (!langs.length) {
      toast.error('Select a language');
      return;
    }
    try {
      const qs = langs.join(',');
      const res = await fetch(`/api/outlet/${tenant}/menu/i18n/export?langs=${qs}`);
      if (!res.ok) throw new Error(await res.text());
      const csv = await res.text();
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const date = new Date().toISOString().slice(0, 10);
      const a = document.createElement('a');
      a.href = url;
      a.download = `menu_i18n_${tenant}_${date}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Export complete');
    } catch (err: any) {
      toast.error(err.message || 'Export failed');
    }
  };

  return (
    <div className="flex items-center space-x-2">
      {LANGS.map((l) => (
        <label key={l} className="flex items-center space-x-1">
          <input
            type="checkbox"
            checked={langs.includes(l)}
            onChange={() => toggleLang(l)}
          />
          <span>{l.toUpperCase()}</span>
        </label>
      ))}
      <Button onClick={doExport}>Export CSV</Button>
    </div>
  );
}
