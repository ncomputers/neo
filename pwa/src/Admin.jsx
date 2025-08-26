import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
        <div
          role="alert"
          className="mb-4 border border-warning bg-warning p-2 text-white"
        >
          {warning}
        </div>
      )}
      <h1 className="text-2xl font-bold">Admin Area</h1>
      <div className="mt-4">
        <Link
          to="/admin/troubleshoot"
          className="text-blue-600 underline hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Troubleshoot common issues
        </Link>
      </div>
    </div>
  )
}
