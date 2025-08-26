import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { apiFetch } from '../api'

export default function CleanerDashboard() {
  const { logo } = useTheme()
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchTables = () => {
    setLoading(true)
    apiFetch('/tables')
      .then((res) => res.json())
      .then((data) => setTables(data.tables || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchTables()
  }, [])

  const markClean = (id) => {
    apiFetch(`/tables/${id}/mark-clean`, { method: 'POST' })
      .then(() => fetchTables())
      .catch((err) => setError(err.message))
  }

  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold mb-4">Cleaner Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && (
        <table className="w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 border">Name</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Action</th>
            </tr>
          </thead>
          <tbody>
            {tables.map((t) => (
              <tr key={t.id}>
                <td className="p-2 border">{t.name}</td>
                <td className="p-2 border capitalize">{t.status}</td>
                <td className="p-2 border text-center">
                  <button
                    aria-label="Mark table clean"
                    className="px-2 py-1 bg-primary text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                    onClick={() => markClean(t.id)}
                  >
                    Mark Clean
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
