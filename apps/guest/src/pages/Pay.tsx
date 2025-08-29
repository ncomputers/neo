import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';

interface Item {
  name: string;
  qty: number;
  price: number;
}

interface Invoice {
  items: Item[];
  tax: number;
  total: number;
  upi?: { pa: string; pn: string };
  onlineUpi?: boolean;
}

export function PayPage() {
  const { orderId } = useParams();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUtr, setShowUtr] = useState(false);
  const [utr, setUtr] = useState('');
  const [showQr, setShowQr] = useState(false);
  const [status, setStatus] = useState<'waiting' | 'success'>('waiting');

  useEffect(() => {
    setError(null);
    fetch(`/api/orders/${orderId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to fetch');
        return r.json();
      })
      .then(setInvoice)
      .catch(() => setError('Failed to load invoice'));
  }, [orderId]);

  const upiLink = invoice?.upi
    ? `upi://pay?pa=${invoice.upi.pa}&pn=${encodeURIComponent(
        invoice.upi.pn
      )}&am=${invoice.total}&tn=Order%20${orderId}`
    : '';

  useEffect(() => {
    let int: ReturnType<typeof setInterval> | undefined;
    if (showQr && status !== 'success') {
      int = setInterval(async () => {
        const res = await fetch(`/api/orders/${orderId}/payment-status`);
        const json = await res.json();
        if (json.status === 'settled') {
          setStatus('success');
          clearInterval(int);
        }
      }, 1000);
    }
    return () => {
      if (int) clearInterval(int);
    };
  }, [showQr, orderId, status]);

  if (error)
    return (
      <div>
        <Header />
        <p>Failed to load invoice.</p>
      </div>
    );

  if (!invoice) return (
    <div>
      <Header />
      <p>Loading...</p>
    </div>
  );

  if (!invoice.onlineUpi) {
    return (
      <div>
        <Header />
        <h1>Invoice</h1>
        <ul>
          {invoice.items.map((it) => (
            <li key={it.name}>
              {it.name} x {it.qty} = {it.price}
            </li>
          ))}
        </ul>
        <p>Tax: {invoice.tax}</p>
        <p>Total: {invoice.total}</p>
        <div data-testid="cashier-qr">
          <p>Show this screen to cashier</p>
          <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${orderId}`}
            alt="qr"
          />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header />
      <h1>Invoice</h1>
      <ul>
        {invoice.items.map((it) => (
          <li key={it.name}>
            {it.name} x {it.qty} = {it.price}
          </li>
        ))}
      </ul>
      <p>Tax: {invoice.tax}</p>
      <p>Total: {invoice.total}</p>
      {!showQr ? (
        <>
          <a href={upiLink}>PhonePe</a>
          <a href={upiLink}>GPay</a>
          <a href={upiLink}>Paytm</a>
          <button onClick={() => setShowUtr(true)}>I've paid</button>
        </>
      ) : (
        <div data-testid="cashier-qr">
          <p>Show this screen to cashier</p>
          <img
            src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${orderId}`}
            alt="qr"
          />
          <p style={{ color: status === 'success' ? 'green' : undefined }}>
            {status === 'success'
              ? 'Payment successful'
              : 'Waiting for verification'}
          </p>
        </div>
      )}
      {showUtr && (
        <div role="dialog">
          <label>
            UTR
            <input
              value={utr}
              onChange={(e) => setUtr(e.target.value)}
            />
          </label>
          <button
            onClick={async () => {
              const res = await fetch(`/api/orders/${orderId}/utr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ orderId, utr }),
              });
              if (res.ok) {
                setShowUtr(false);
                setShowQr(true);
              }
            }}
          >
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
