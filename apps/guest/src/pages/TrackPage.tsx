import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';
import { useTranslation } from 'react-i18next';

interface EventData {
  eta: string;
  status: string;
  billable: boolean;
}

export function TrackPage() {
  const { orderId } = useParams();
  const [eta, setEta] = useState('');
  const [status, setStatus] = useState('');
  const [billable, setBillable] = useState(false);
  const [error, setError] = useState(false);
  const { t } = useTranslation();

    useEffect(() => {
      const es = new EventSource(`/api/orders/${orderId}/events`);
      es.onmessage = (e) => {
        const data: EventData = JSON.parse(e.data);
        setEta(data.eta);
        setStatus(data.status);
        setBillable(data.billable);
        setError(false);
      };
      es.onerror = () => {
        setError(true);
        es.close();
      };
      return () => es.close();
    }, [orderId, error]);

  return (
    <div>
      <Header />
      <p>ETA: {eta}</p>
        <p>Status: {status}</p>
        {error && <button onClick={() => setError(false)}>{t('retry')}</button>}
        {billable && <button>Get bill/Pay now</button>}
      </div>
    );
  }
