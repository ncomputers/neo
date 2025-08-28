import { useEffect, useState } from 'react';
import { API_BASE } from '../env';
import { useSSE } from '@neo/api';

export function Health() {
  const [ok, setOk] = useState(false);
  const [sse, setSse] = useState<'pending' | 'ok' | 'unsupported'>('pending');

  useEffect(() => {
    fetch(`${API_BASE}/status.json`)
      .then((r) => setOk(r.ok))
      .catch(() => setOk(false));
  }, []);

  useSSE(`${API_BASE}/sse/ping`, {
    onMessage: () => setSse('ok'),
    onError: () => setSse('unsupported'),
  });

  return (
    <div className="space-y-2">
      <div
        className={
          ok
            ? 'w-3 h-3 rounded-full bg-green-500'
            : 'w-3 h-3 rounded-full bg-red-500'
        }
      />
      {sse === 'unsupported' && <div>SSE unsupported</div>}
    </div>
  );
}
