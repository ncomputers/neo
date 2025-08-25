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
  const [orders, setOrders] = useState([])

  useEffect(() => {
    apiFetch('/tables/1/bill')
      .then((res) => res.json())
      .then((data) => setBill(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  // Listen for service worker sync updates
  useEffect(() => {
    if (navigator.serviceWorker) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data?.type === 'ORDERS_SYNCED') {
          const synced = new Set(event.data.op_ids)
          setOrders((orders) =>
            orders.map((o) =>
              synced.has(o.op_id) ? { ...o, status: 'synced' } : o
            )
          )
        }
      })
    }
  }, [])

  function addSampleItem() {
    if (navigator.serviceWorker?.controller) {
      const channel = new MessageChannel()
      channel.port1.onmessage = (event) => {
        const { op_id } = event.data
        setOrders((os) => [
          ...os,
          { op_id, item: 'Coffee', status: 'pending' },
        ])
      }
      navigator.serviceWorker.controller.postMessage(
        {
          type: 'QUEUE_ORDER',
          order: {
            table_code: 'T1',
            items: [{ item_id: '1', qty: 1 }],
          },
        },
        [channel.port2]
      )
    }
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
      <div className="mt-4">
        <button
          onClick={addSampleItem}
          className="px-2 py-1 border rounded"
        >
          Add Coffee
        </button>
        <ul className="mt-4 space-y-2">
          {orders.map((o) => (
            <li key={o.op_id} className="flex justify-between border p-2">
              <span>{o.item}</span>
              <span
                className={
                  o.status === 'pending'
                    ? 'text-yellow-600'
                    : 'text-green-600'
                }
              >
                {o.status}
              </span>
            </li>
          ))}
        </ul>
      </div>
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
