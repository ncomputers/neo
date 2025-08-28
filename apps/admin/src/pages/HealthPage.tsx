import { useEffect, useState } from 'react';
import { API_BASE } from '../env';
import { useCounterStore } from '../store';
import { DemoForm } from '../components/DemoForm';

export function HealthPage() {
  const [ok, setOk] = useState(false);
  const count = useCounterStore((s) => s.count);

  useEffect(() => {
    fetch(`${API_BASE}/status.json`)
      .then((r) => setOk(r.ok))
      .catch(() => setOk(false));
  }, []);

  return (
    <div className="space-y-2">
      <div
        className={
          ok
            ? 'w-3 h-3 rounded-full bg-green-500'
            : 'w-3 h-3 rounded-full bg-red-500'
        }
      />
      <div>{count}</div>
      <DemoForm />
    </div>
  );
}
