import { useEffect, useState } from 'react'

const TENANT_ID = import.meta.env.VITE_TENANT_ID || ''

export default function InvoiceLink({ invoiceId }) {
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    if (!('caches' in window)) return
    const cacheName = `invoice-${TENANT_ID || 'default'}`
    caches
      .open(cacheName)
      .then((cache) => cache.match(`/invoice/${invoiceId}/pdf`))
      .then((res) => setOffline(!!res))
  }, [invoiceId])

  return (
    <a
      href={`/invoice/${invoiceId}/pdf`}
      className="text-blue-500 underline inline-flex items-center"
    >
      Invoice #{invoiceId}
      {offline && (
        <span className="ml-2 text-xs bg-green-100 text-green-800 px-1 rounded">
          Available offline
        </span>
      )}
    </a>
  )
}
