import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { apiFetch } from '../api'
import LimitsUsageWidget from '../components/LimitsUsageWidget'

export default function AdminDashboard() {
  const { logo } = useTheme()
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/tables')
      .then((res) => res.json())
      .then((data) => setTables(data.tables || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold mb-4">Admin Dashboard</h2>
      <LimitsUsageWidget />
      {loading && <p>Loading...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && (
        <table className="w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 border">Name</th>
              <th className="p-2 border">Status</th>
            </tr>
          </thead>
          <tbody>
            {tables.map((t) => (
              <tr key={t.id}>
                <td className="p-2 border">{t.name}</td>
                <td className="p-2 border capitalize">{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <footer className="mt-8 text-sm text-gray-600">
        <a
          href="/legal/subprocessors"
          className="mx-2 hover:underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Subprocessors
        </a>
        <a
          href="/legal/sla"
          className="mx-2 hover:underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          SLA
        </a>
      </footer>
    </div>
  )
}
