import { useEffect, useState } from 'react'
import { apiFetch } from './api'

export default function Admin() {
  const [warning, setWarning] = useState('')

  useEffect(() => {
    apiFetch(`/time/skew`)
      .then((r) => r.json())
      .then((data) => {
        const serverMs = data.epoch * 1000
        const skew = Math.abs(Date.now() - serverMs)
        if (skew > 120000) {
          setWarning('Your device clock is out of sync. Please correct it.')
        }
      })
      .catch(() => {})
  }, [])

  return (
    <div className="p-4">
      {warning && (
        <div className="mb-4 border border-yellow-400 bg-yellow-100 p-2 text-yellow-800">
          {warning}
        </div>
      )}
      <h1 className="text-2xl font-bold">Admin Area</h1>
    </div>
  )
}
