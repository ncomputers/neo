import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const LATENCY_THRESHOLD = 2000;

export function PoorConnectionBanner() {
  const [poor, setPoor] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      if (!navigator.onLine) {
        if (!cancelled) setPoor(true);
        return;
      }
      try {
        const start = performance.now();
        await fetch(`/status.json?c=${Date.now()}`, { cache: 'no-store' });
        const latency = performance.now() - start;
        if (!cancelled) setPoor(latency > LATENCY_THRESHOLD);
      } catch {
        if (!cancelled) setPoor(true);
      }
    };
    check();
    const id = setInterval(check, 15000);
    window.addEventListener('online', check);
    window.addEventListener('offline', check);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener('online', check);
      window.removeEventListener('offline', check);
    };
  }, []);

  if (!poor) return null;

  return (
    <div className="text-center text-xs bg-yellow-200">{t('poor_connection')}</div>
  );
}
