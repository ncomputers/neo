import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';

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

  useEffect(() => {
    const es = new EventSource(`/api/orders/${orderId}/events`);
    es.onmessage = (e) => {
      const data: EventData = JSON.parse(e.data);
      setEta(data.eta);
      setStatus(data.status);
      setBillable(data.billable);
    };
    return () => es.close();
  }, [orderId]);

  return (
    <div>
      <Header />
      <p>ETA: {eta}</p>
      <p>Status: {status}</p>
      {billable && <button>Get bill/Pay now</button>}
    </div>
  );
}
