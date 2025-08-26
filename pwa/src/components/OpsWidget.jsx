import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

export default function OpsWidget() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch('/admin/ops/summary')
      .then((res) => res.json())
      .then((json) => setData(json.data))
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="text-danger">{error}</p>
  if (!data) return <p>Loading...</p>

  const pct = (v) => (v * 100).toFixed(1)
  const seconds = (v) => `${Math.round(v)}s`

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">Ops</h3>
      <div className="text-sm space-y-1">
        <div className="flex justify-between"><span>Uptime</span><span>{data.uptime}</span></div>
        <div className="flex justify-between"><span>Webhook Success</span><span>{pct(data.webhook_success_rate)}%</span></div>
        <div className="flex justify-between"><span>Breaker Open Time</span><span>{seconds(data.breaker_open_time)}</span></div>
        <div className="flex justify-between"><span>Median KOT Prep</span><span>{data.median_kot_prep_time ? seconds(data.median_kot_prep_time) : 'N/A'}</span></div>
      </div>
    </div>
  )
}
