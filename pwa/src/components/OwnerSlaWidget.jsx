import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

export default function OwnerSlaWidget() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/owner/sla')
      .then((res) => res.json())
      .then((json) => setData(json.data))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="text-danger">{error}</p>
  if (!data) return <p>Loading...</p>

  const pct = (v) => `${(v * 100).toFixed(1)}%`
  const seconds = (v) => `${Math.round(v)}s`
  const arrow = (good) => (good ? '↑' : '↓')

  return (
    <div className="border p-2 rounded text-sm space-y-1">
      <div className="flex justify-between">
        <span>Uptime</span>
        <span>
          {pct(data.uptime_7d / 100)} {arrow(data.uptime_7d >= 99.9)}
        </span>
      </div>
      <div className="flex justify-between">
        <span>Webhook Success</span>
        <span>{pct(data.webhook_success)}</span>
      </div>
      <div className="flex justify-between">
        <span>Median Prep</span>
        <span>
          {seconds(data.median_prep)} {arrow(data.median_prep < 600)}
        </span>
      </div>
      <div className="flex justify-between">
        <span>KOT Delay Alerts</span>
        <span>
          {data.kot_delay_alerts} {arrow(data.kot_delay_alerts === 0)}
        </span>
      </div>
    </div>
  )
}
