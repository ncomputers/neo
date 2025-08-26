import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

export default function PilotTelemetryWidget() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/admin/pilot/telemetry')
      .then((res) => res.json())
      .then((json) => setData(json.data))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="text-danger">{error}</p>
  if (!data) return <p>Loading...</p>

  const pct = (v) => `${v.toFixed(1)}%`
  const secs = (v) => `${Math.round(v)}s`

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">Pilot Telemetry</h3>
      <div className="text-sm space-y-1">
        <div className="flex justify-between"><span>Orders/min</span><span>{data.orders_per_min.toFixed(1)}</span></div>
        <div className="flex justify-between"><span>Avg Prep</span><span>{secs(data.avg_prep_s)}</span></div>
        <div className="flex justify-between"><span>Breaker Open</span><span>{pct(data.webhook_breaker_open_pct)}</span></div>
        <div className="flex justify-between"><span>KOT Queue Oldest</span><span>{secs(data.kot_queue_oldest_s)}</span></div>
        <div className="flex justify-between"><span>95p Latency</span><span>{Math.round(data.p95_latency_ms)}ms</span></div>
        <div className="flex justify-between"><span>Error Rate</span><span>{pct(data.error_rate_5m * 100)}</span></div>
        <div className="flex justify-between"><span>SSE Clients</span><span>{data.sse_clients}</span></div>
      </div>
    </div>
  )
}
