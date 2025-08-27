import { useEffect, useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { apiFetch } from '../api'
import InvoiceLink from '../components/InvoiceLink'
import StatusPill from '../components/StatusPill'

export default function CashierDashboard() {
  const { logo } = useTheme()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [invoices, setInvoices] = useState([])
  const [refundInfo, setRefundInfo] = useState({})

  useEffect(() => {
    apiFetch('/orders')
      .then((res) => res.json())
      .then((data) => setOrders(data.orders || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
    apiFetch('/invoices?limit=50')
      .then((res) => res.json())
      .then((data) => setInvoices(data.invoices || []))
      .catch(() => {})
  }, [])

  const handleRefund = (invoiceId) => {
    if (!window.confirm('Are you sure?')) return
    const key = crypto.randomUUID()
    apiFetch(`/payments/${invoiceId}/refund`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
    })
      .then(() => {
        setRefundInfo((prev) => ({ ...prev, [invoiceId]: key }))
      })
      .catch(() => {})
  }

  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold mb-4">Cashier Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && (
        <>
          <table className="w-full border mb-6">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 border">Table</th>
                <th className="p-2 border">Item</th>
                <th className="p-2 border">Qty</th>
                <th className="p-2 border">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={`${o.table_id}-${o.index}`}>
                  <td className="p-2 border">{o.table_id}</td>
                  <td className="p-2 border">{o.item}</td>
                  <td className="p-2 border">{o.quantity}</td>
                  <td className="p-2 border capitalize">{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {invoices.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Recent invoices</h3>
              <ul className="space-y-1">
                {invoices.map((inv) => (
                  <li key={inv.invoice_id}>
                    <InvoiceLink invoiceId={inv.invoice_id} />
                    <button
                      onClick={() => handleRefund(inv.invoice_id)}
                      className="ml-2 text-sm text-red-600 underline"
                    >
                      Refund
                    </button>
                    {refundInfo[inv.invoice_id] && (
                      <span className="ml-2 text-xs text-gray-500">
                        Key: {refundInfo[inv.invoice_id]}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      <footer className="mt-8 text-sm text-gray-600 flex items-center space-x-2">
        <StatusPill />
        <a
          href="/legal/terms"
          className="mx-2 hover:underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Terms
        </a>
        <a
          href="/legal/refund"
          className="mx-2 hover:underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Refund
        </a>
        <a
          href="/legal/contact"
          className="mx-2 hover:underline focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Contact
        </a>
      </footer>
    </div>
  )
}
