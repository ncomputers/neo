import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { apiFetch } from '../api'

export default function KitchenDashboard() {
  const { logo } = useTheme()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [printerStale, setPrinterStale] = useState(false)
  const [kotDelay, setKotDelay] = useState(false)

  const fetchOrders = () => {
    setLoading(true)
    apiFetch('/kds/queue')
      .then((res) => res.json())
      .then((data) => {
        setOrders(data.orders || [])
        setPrinterStale(data.printer_stale)
        setKotDelay(data.kot_delay)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const updateOrder = (tableId, index, action) => {
    apiFetch(`/orders/${tableId}/${index}/${action}`, {
      method: 'POST',
    })
      .then(() => fetchOrders())
      .catch((err) => setError(err.message))
  }

  return (
    <div className="p-4">
      {kotDelay && (
        <div
          className="mb-4 rounded bg-yellow-600 p-2 text-white"
          data-testid="kot-delay-alert"
        >
          Kitchen is behind. Oldest ticket delayed.
        </div>
      )}
      {printerStale && (
        <div
          role="alert"
          className="mb-4 rounded bg-red-600 p-2 text-white"
          data-testid="printer-alert"
        >
          Printer offline. Tickets queued.
        </div>
      )}
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold mb-4">Kitchen Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && (
        <table className="w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 border">Table</th>
              <th className="p-2 border">Item</th>
              <th className="p-2 border">Qty</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={`${o.table_id}-${o.index}`}>
                <td className="p-2 border">{o.table_id}</td>
                <td className="p-2 border">{o.item}</td>
                <td className="p-2 border">{o.quantity}</td>
                <td className="p-2 border capitalize">{o.status}</td>
                <td className="p-2 border space-x-2 text-center">
                  <button
                    aria-label="Accept order"
                    className="px-2 py-1 bg-success text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success"
                    onClick={() => updateOrder(o.table_id, o.index, 'accept')}
                  >
                    Accept
                  </button>
                  <button
                    aria-label="Reject order"
                    className="px-2 py-1 bg-danger text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-danger"
                    onClick={() => updateOrder(o.table_id, o.index, 'reject')}
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
