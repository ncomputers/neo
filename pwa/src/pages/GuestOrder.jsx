import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { useOrderStatus } from '../hooks/useOrderStatus'
import { apiFetch } from '../api'

export default function GuestOrder() {
  const { logo } = useTheme()
  const { status, eta } = useOrderStatus('order-1')
  const [bill, setBill] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [ops, setOps] = useState([])

  useEffect(() => {
    apiFetch('/tables/1/bill')
      .then((res) => res.json())
      .then((data) => setBill(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const handler = (event) => {
      if (event.data?.type === 'QUEUE_STATUS') setOps(event.data.ops)
    }
    navigator.serviceWorker.addEventListener('message', handler)
    return () => navigator.serviceWorker.removeEventListener('message', handler)
  }, [])

  const addSample = () => {
    const op = {
      op_id: crypto.randomUUID(),
      table_code: '1',
      items: [{ item_id: 'demo', qty: 1 }],
      synced: false,
    }
    navigator.serviceWorker.controller?.postMessage({ type: 'QUEUE_ORDER_OP', op })
    setOps((prev) => [...prev, op])
  }

  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold">Guest Ordering</h2>
      <p className="mt-2">Status: {status}</p>
      <p className="mt-1">ETA: {eta}</p>
      {loading && <p>Loading bill...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {bill && (
        <div className="mt-4">
          <h3 className="font-semibold">Current Bill: {bill.total}</h3>
        </div>
      )}
      <button
        onClick={addSample}
        className="mt-4 rounded bg-blue-600 px-2 py-1 text-white"
      >
        Add Sample Item
      </button>
      <ul className="mt-4">
        {ops.map((op) => (
          <li key={op.op_id} className="mb-1">
            {op.items[0].item_id} x {op.items[0].qty}{' '}
            <span
              className={op.synced ? 'text-green-600' : 'text-yellow-600'}
            >
              {op.synced ? 'synced' : 'pending'}
            </span>
          </li>
        ))}
      </ul>
      <footer className="mt-8 text-sm text-gray-500">
        <a href="/legal/privacy" className="mx-2 hover:underline">
          Privacy
        </a>
        <a href="/legal/terms" className="mx-2 hover:underline">
          Terms
        </a>
      </footer>
    </div>
  )
}
