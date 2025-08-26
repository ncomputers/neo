import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

export default function Billing() {
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/billing')
      .then((r) => r.json())
      .then((data) => setInfo(data.data))
      .catch((e) => setError(e.message))
  }, [])

  if (error) {
    return (
      <div className="p-4 text-red-500">
        {error}
      </div>
    )
  }
  if (!info) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="p-4">
      {info.grace && (
        <div className="mb-4 border border-yellow-400 bg-yellow-100 p-2 text-yellow-800">
          Subscription expired. Renew to continue service.
        </div>
      )}
      <h2 className="mb-4 text-xl font-bold">Billing</h2>
      <p>Plan: {info.plan || 'unknown'}</p>
      {info.next_renewal && (
        <p>
          Next renewal: {new Date(info.next_renewal).toLocaleDateString()}
        </p>
      )}
      {info.pay_url && (
        <a
          href={info.pay_url}
          className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 text-white"
          target="_blank"
          rel="noopener noreferrer"
        >
          Pay Now
        </a>
      )}
    </div>
  )
}

