import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Header } from '../components/Header';

export function OfflinePage() {
  const [name, setName] = useState('');
  const { t } = useTranslation();
  useEffect(() => {
    const info = JSON.parse(localStorage.getItem('outletInfo') || '{}');
    setName(info.name || '');
  }, []);
  return (
    <div>
      <Header />
      {name && <h1>{name}</h1>}
      <p>{t('offline_notice')}</p>
    </div>
  );
}
