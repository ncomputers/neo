import { useState } from 'react'
import { apiFetch } from './api'

export default function Troubleshoot() {
  const [printerStatus, setPrinterStatus] = useState('')
  const [timeStatus, setTimeStatus] = useState('')
  const [dnsStatus, setDnsStatus] = useState('')

  const checkPrinter = () => {
    apiFetch('/printer/status')
      .then((r) => {
        if (r.ok) {
          setPrinterStatus('Printer reachable.')
        } else {
          setPrinterStatus('Printer offline. Check power and network.')
        }
      })
      .catch(() => {
        setPrinterStatus('Printer offline. Check power and network.')
      })
  }

  const checkTime = () => {
    apiFetch('/time/skew')
      .then((r) => r.json())
      .then((data) => {
        const serverMs = data.epoch * 1000
        const skew = Math.abs(Date.now() - serverMs)
        if (skew > 120000) {
          setTimeStatus('Device clock is out of sync. Please correct it.')
        } else {
          setTimeStatus('Device clock is accurate.')
        }
      })
      .catch(() => {
        setTimeStatus('Unable to check time skew.')
      })
  }

  const checkDns = () => {
    fetch('https://example.com', { mode: 'no-cors' })
      .then(() => {
        setDnsStatus('DNS resolution looks good.')
      })
      .catch(() => {
        setDnsStatus('DNS lookup failed. Check your network settings.')
      })
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Troubleshooting</h1>

      <div className="mt-4">
        <h2 className="font-semibold">Printer offline</h2>
        <button
          className="mt-2 rounded bg-blue-600 px-3 py-1 text-white"
          onClick={checkPrinter}
        >
          Check
        </button>
        {printerStatus && <p className="mt-2">{printerStatus}</p>}
      </div>

      <div className="mt-6">
        <h2 className="font-semibold">Time skew</h2>
        <button
          className="mt-2 rounded bg-blue-600 px-3 py-1 text-white"
          onClick={checkTime}
        >
          Check
        </button>
        {timeStatus && <p className="mt-2">{timeStatus}</p>}
      </div>

      <div className="mt-6">
        <h2 className="font-semibold">DNS issues</h2>
        <button
          className="mt-2 rounded bg-blue-600 px-3 py-1 text-white"
          onClick={checkDns}
        >
          Check
        </button>
        {dnsStatus && <p className="mt-2">{dnsStatus}</p>}
      </div>
    </div>
  )
}
