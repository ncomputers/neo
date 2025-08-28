import { useEffect, useState } from 'react';
import { API_BASE } from '../env';

export function Health() {
  const [ok, setOk] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/status.json`)
      .then((r) => setOk(r.ok))
      .catch(() => setOk(false));
  }, []);

  return (
    <div
      className={
        ok
          ? 'w-3 h-3 rounded-full bg-green-500'
          : 'w-3 h-3 rounded-full bg-red-500'
      }
    />
  );
}
