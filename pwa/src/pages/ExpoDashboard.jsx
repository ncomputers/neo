import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { apiFetch } from '../api'

export default function ExpoDashboard() {
  const { logo } = useTheme()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchOrders = () => {
    setLoading(true)
    apiFetch('/kds/expo')
      .then((res) => res.json())
      .then((data) => {
        setOrders(data.tickets || [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const markPicked = (id) => {
    apiFetch(`/kds/expo/${id}/picked`, { method: 'POST' })
      .then(() => fetchOrders())
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    const handler = (e) => {
      // Hotkey support: "P" marks the last order as picked
      if (e.key === 'p' || e.key === 'P') {
        if (orders.length > 0) {
          markPicked(orders[orders.length - 1].order_id)
        }
        return
      }
      const idx = parseInt(e.key, 10)
      if (!isNaN(idx) && idx > 0 && idx <= orders.length) {
        markPicked(orders[idx - 1].order_id)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [orders])

  return (
    <div className="p-4">
      {logo && (
        <img src={logo} alt="Logo" className="h-16 mb-4" loading="lazy" />
      )}
      <h2 className="text-xl font-bold mb-4">Expo Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && (
        <ul className="space-y-4">
          {orders.map((o, idx) => (
            <li key={o.order_id} className="border p-2 rounded">
              <div className="flex justify-between">
                <span className="font-semibold">
                  Table {o.table}
                  {o.allergen_badges.length > 0 && (
                    <span className="ml-2 rounded bg-red-100 px-1 text-red-800 text-xs">
                      Allergy
                    </span>
                  )}
                </span>
                <span className="text-sm text-gray-600">
                  {Math.round(o.age_s / 60)}m
                </span>
              </div>
              <button
                className="mt-2 bg-blue-600 text-white px-2 py-1 rounded"
                onClick={() => markPicked(o.order_id)}
              >
                Picked
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
