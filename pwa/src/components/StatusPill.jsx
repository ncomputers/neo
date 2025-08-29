import { useEffect, useState } from 'react'

export default function StatusPill() {
  const [state, setState] = useState(null)

  useEffect(() => {
    fetch('/status.json')
      .then((res) => res.json())
      .then((json) => setState(json.state))
      .catch(() => {})
  }, [])

  const color =
    state === 'ok'
      ? 'bg-green-500'
      : state === 'degraded'
        ? 'bg-amber-500'
        : state === 'outage'
          ? 'bg-red-500'
          : 'bg-gray-400'

  return (
    <span
      data-testid="status-pill"
      className={`inline-block w-3 h-3 rounded-full ${color}`}
    ></span>
  )
}
