import { useRef, useState } from 'react';
import { Button, toast } from '@neo/ui';

const LANGS = ['en', 'hi'];

interface Result {
  updated_rows: number;
  skipped: number;
  errors?: string[];
  audit_id?: string;
}

interface Props {
  tenant: string;
}

export function MenuI18nImport({ tenant }: Props) {
  const [langs, setLangs] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const toggleLang = (l: string) => {
    setLangs((prev) =>
      prev.includes(l) ? prev.filter((x) => x !== l) : [...prev, l]
    );
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const form = new FormData();
      form.append('file', file);
      const qs = langs.length ? `?langs=${langs.join(',')}` : '';
      const res = await fetch(`/api/outlet/${tenant}/menu/i18n/import${qs}`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setResult(json);
      toast.success('Import complete');
    } catch (err: any) {
      toast.error(err.message || 'Import failed');
    }
    e.target.value = '';
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
      <input
        data-testid="i18n-import-file"
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFile}
      />
      <Button onClick={() => inputRef.current?.click()}>Import CSV</Button>
      {result && (
        <div className="ml-2 text-sm" data-testid="import-result">
          <span>Updated: {result.updated_rows}</span>
          <span className="ml-2">Skipped: {result.skipped}</span>
          {result.errors && result.errors.length > 0 && (
            <ul>
              {result.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
          {result.audit_id && <span className="ml-2">Audit: {result.audit_id}</span>}
        </div>
      )}
    </div>
  );
}
