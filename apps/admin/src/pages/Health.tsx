import { useEffect, useState } from 'react';

export function Health() {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE}/status.json`)
      .then((r) => setOk(r.ok))
      .catch(() => setOk(false));
  }, []);
  return (
    <div className={ok ? 'w-3 h-3 rounded-full bg-green-500' : 'w-3 h-3 rounded-full bg-red-500'} />
  );
}
