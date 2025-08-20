import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { useOrderStatus } from '../hooks/useOrderStatus'

export default function GuestOrder() {
  const { logo } = useTheme()
  const { status, eta } = useOrderStatus('order-1')
  const [bill, setBill] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('http://localhost:4000/tables/1/bill')
      .then((res) => res.json())
      .then((data) => setBill(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

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
    </div>
  )
}
