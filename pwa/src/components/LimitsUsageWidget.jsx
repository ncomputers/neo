import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

function Bar({ label, usage }) {
  const limit = usage.limit
  const used = usage.used
  const percent = limit ? Math.min((used / limit) * 100, 100) : 0
  const color =
    percent >= 100 ? 'bg-danger' : percent >= 80 ? 'bg-warning' : 'bg-success'
  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm mb-1">
        <span>{label}</span>
        <span>
          {used}
          {limit ? ` / ${limit}` : ''}
        </span>
      </div>
      {limit ? (
        <div className="w-full bg-gray-200 rounded h-2">
          <div
            className={`h-2 rounded ${color}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      ) : null}
    </div>
  )
}

export default function LimitsUsageWidget() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/limits/usage')
      .then((res) => res.json())
      .then((json) => setData(json))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="text-danger">{error}</p>
  if (!data) return <p>Loading...</p>

  const entries = [
    { key: 'tables', label: 'Tables' },
    { key: 'menu_items', label: 'Items' },
    { key: 'images_mb', label: 'Images (MB)' },
    { key: 'daily_exports', label: 'Exports' },
  ]

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">Usage</h3>
      {entries.map(({ key, label }) =>
        data[key] ? <Bar key={key} label={label} usage={data[key]} /> : null,
      )}
      <a
        href="mailto:support@example.com?subject=Request%20more%20quota"
        className="text-sm text-primary underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        target="_blank"
        rel="noopener noreferrer"
      >
        Request more
      </a>
    </div>
  )
}
