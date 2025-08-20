import { useEffect, useState } from 'react'

export function useOrderStatus(orderId) {
  const [status, setStatus] = useState('pending')
  const [eta, setEta] = useState('')

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:4000/orders/${orderId}`)
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.status) setStatus(data.status)
        if (data.eta) setEta(data.eta)
      } catch {
        // ignore parsing errors
      }
    }
    return () => ws.close()
  }, [orderId])

  return { status, eta }
}
