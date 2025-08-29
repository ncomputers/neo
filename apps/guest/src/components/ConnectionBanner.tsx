import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export function ConnectionBanner() {
  const [bad, setBad] = useState(false);
  const { t } = useTranslation();
  useEffect(() => {
    const update = () => {
      const conn: any = navigator.connection;
      const poor = !navigator.onLine || (conn && conn.downlink && conn.downlink < 0.5);
      setBad(poor);
    };
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);
  if (!bad) return null;
  return (
    <div className="text-center text-xs bg-yellow-200">{t('poor_connection')}</div>
  );
}
