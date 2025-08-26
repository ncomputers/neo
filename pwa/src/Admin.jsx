import { useEffect, useState } from 'react'
import { apiFetch } from './api'

export default function Admin() {
  const [skewAdvice, setSkewAdvice] = useState('')

  useEffect(() => {
    const clientTs = Date.now()
    apiFetch(`/time/skew?client_ts=${clientTs}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.skew_ms && Math.abs(data.skew_ms) > 120000) {
          setSkewAdvice(data.advice)
        }
      })
      .catch(() => {})
  }, [])

  return (
    <div className="p-4">
      {skewAdvice && (
        <div className="mb-4 border border-yellow-400 bg-yellow-100 p-2 text-yellow-800">
          {skewAdvice}
        </div>
      )}
      <h1 className="text-2xl font-bold">Admin Area</h1>
    </div>
  )
}
