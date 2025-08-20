import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'

export default function KitchenDashboard() {
  const { logo } = useTheme()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchOrders = () => {
    setLoading(true)
    fetch('http://localhost:4000/orders')
      .then((res) => res.json())
      .then((data) => setOrders(data.orders || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const updateOrder = (tableId, index, action) => {
    fetch(`http://localhost:4000/orders/${tableId}/${index}/${action}`, {
      method: 'POST',
    })
      .then(() => fetchOrders())
      .catch((err) => setError(err.message))
  }

  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold mb-4">Kitchen Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
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
                    className="px-2 py-1 bg-green-500 text-white rounded"
                    onClick={() => updateOrder(o.table_id, o.index, 'accept')}
                  >
                    Accept
                  </button>
                  <button
                    className="px-2 py-1 bg-red-500 text-white rounded"
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
