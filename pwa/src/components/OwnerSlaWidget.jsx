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
  const trendArrow = (v) => (v >= 0 ? '↑' : '↓')

  // Uptime thresholds: >=99.9% green, >=99% yellow, otherwise red
  const uptimeColor = (v) =>
    v >= 99.9 ? 'text-green-600' : v >= 99 ? 'text-yellow-600' : 'text-red-600'

  // Webhook success thresholds: >=99% green, >=95% yellow, otherwise red
  const webhookColor = (v) =>
    v >= 0.99 ? 'text-green-600' : v >= 0.95 ? 'text-yellow-600' : 'text-red-600'

  // Median prep time thresholds: <10min green, <15min yellow, else red
  const prepColor = (v) =>
    v < 600 ? 'text-green-600' : v < 900 ? 'text-yellow-600' : 'text-red-600'

  // KOT delay alerts thresholds: 0 green, <=3 yellow, >3 red
  const kotColor = (v) =>
    v === 0 ? 'text-green-600' : v <= 3 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="border p-2 rounded text-sm space-y-1">
      <div className="flex justify-between">
        <span>Uptime</span>
        <span className={uptimeColor(data.uptime_7d)}>
          {pct(data.uptime_7d / 100)} {trendArrow(data.uptime_trend)}
        </span>
      </div>
      <div className="flex justify-between">
        <span>Webhook Success</span>
        <span className={webhookColor(data.webhook_success)}>
          {pct(data.webhook_success)} {trendArrow(data.webhook_success_trend)}
        </span>
      </div>
      <div className="flex justify-between">
        <span>Median Prep</span>
        <span className={prepColor(data.median_prep)}>
          {seconds(data.median_prep)} {trendArrow(data.median_prep_trend)}
        </span>
      </div>
      <div className="flex justify-between">
        <span>KOT Delay Alerts</span>
        <span className={kotColor(data.kot_delay_alerts)}>
          {data.kot_delay_alerts} {trendArrow(data.kot_delay_alerts_trend)}
        </span>
      </div>
    </div>
  )
}
