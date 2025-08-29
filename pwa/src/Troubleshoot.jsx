import { useState } from 'react'
import { apiFetch } from './api'

export default function Troubleshoot() {
  const [results, setResults] = useState(null)

  const runChecks = () => {
    const epoch = Date.now()
    apiFetch(`/admin/troubleshoot?client_epoch=${epoch}`, {
      headers: {
        'X-App-Version': import.meta.env.VITE_APP_VERSION || '',
      },
    })
      .then((r) => r.json())
      .then(setResults)
      .catch(() => setResults({ error: 'Failed to run checks' }))
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Troubleshooting</h1>
      <button
        className="mt-4 rounded bg-blue-600 px-3 py-1 text-white"
        onClick={runChecks}
      >
        Run checks
      </button>
      {results && !results.error && (
        <ul className="mt-4 space-y-4">
          <li>
            <strong>Printer heartbeat:</strong>{' '}
            {results.printer.ok ? 'Pass' : 'Fail'} {results.printer.next}
          </li>
          <li>
            <strong>Time skew:</strong> {results.time.ok ? 'Pass' : 'Fail'}{' '}
            {results.time.next}
          </li>
          <li>
            <strong>DNS/latency:</strong> {results.dns.ok ? 'Pass' : 'Fail'}{' '}
            {results.dns.next}
          </li>
          <li>
            <strong>Software version:</strong>{' '}
            {results.version.ok ? 'Pass' : 'Fail'} {results.version.next}
          </li>
        </ul>
      )}
      {results && results.error && (
        <p className="mt-4 text-red-600">{results.error}</p>
      )}
    </div>
  )
}
