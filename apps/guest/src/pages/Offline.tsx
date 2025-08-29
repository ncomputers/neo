import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Header } from '../components/Header';

export function Offline() {
  const [name, setName] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const info = JSON.parse(localStorage.getItem('outletInfo') || '{}');
    setName(info.name || '');
  }, []);

  return (
    <div className="p-4 text-center space-y-2">
      <Header />
      {name && <h1>{name}</h1>}
      <p>{t('offline_notice')}</p>
      <p>{t('cached_menu_hint')}</p>
      <button onClick={() => window.location.reload()}>{t('retry')}</button>
    </div>
  );
}
