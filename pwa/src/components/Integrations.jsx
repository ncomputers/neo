import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

export default function Integrations() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [urls, setUrls] = useState({})
  const [reports, setReports] = useState({})

  useEffect(() => {
    apiFetch('/admin/integrations')
      .then((res) => res.json())
      .then((json) => setItems(json.data))
      .catch((err) => setError(err.message))
  }, [])

  const probe = (type) => {
    const url = urls[type] || ''
    apiFetch(`/admin/integrations/${type}/probe`, {
      method: 'POST',
      body: JSON.stringify({ url }),
    })
      .then((res) => res.json())
      .then((json) => setReports({ ...reports, [type]: json.data }))
      .catch((err) =>
        setReports({ ...reports, [type]: { error: err.message } }),
      )
  }

  if (error) return <p className="text-danger">{error}</p>
  if (!items) return <p>Loading...</p>

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">Integrations</h3>
      <ul className="space-y-4 text-sm">
        {items.map((item) => (
          <li key={item.type} className="border p-2">
            <div className="font-medium">{item.name}</div>
            <pre className="bg-gray-100 p-2 mt-1 text-xs overflow-x-auto">
              {JSON.stringify(item.sample_payload, null, 2)}
            </pre>
            <div className="mt-2 flex space-x-2">
              <input
                type="url"
                placeholder="Webhook URL"
                value={urls[item.type] || ''}
                onChange={(e) =>
                  setUrls({ ...urls, [item.type]: e.target.value })
                }
                className="flex-1 border p-1 text-sm"
              />
              <button
                type="button"
                onClick={() => probe(item.type)}
                className="px-2 border rounded"
              >
                Probe
              </button>
            </div>
            {reports[item.type] && (
              <pre className="bg-gray-50 p-2 mt-2 text-xs overflow-x-auto">
                {JSON.stringify(reports[item.type], null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
