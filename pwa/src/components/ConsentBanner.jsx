import { useEffect, useState } from 'react'

export default function ConsentBanner() {
  const [visible, setVisible] = useState(false)
  const [analytics, setAnalytics] = useState(false)
  const [wa, setWa] = useState(false)

  useEffect(() => {
    try {
      const stored = localStorage.getItem('guestConsent')
      if (!stored) {
        setVisible(true)
      }
    } catch (e) {
      setVisible(true)
    }
  }, [])

  const save = () => {
    try {
      localStorage.setItem(
        'guestConsent',
        JSON.stringify({ analytics, wa })
      )
    } catch (e) {
      /* ignore */
    }
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 inset-x-0 bg-gray-800 text-white p-4 space-y-2 text-sm">
      <p>This site uses analytics and may send WhatsApp notifications.</p>
      <label className="block">
        <input
          type="checkbox"
          checked={analytics}
          onChange={(e) => setAnalytics(e.target.checked)}
          className="mr-1"
        />
        Allow analytics
      </label>
      <label className="block">
        <input
          type="checkbox"
          checked={wa}
          onChange={(e) => setWa(e.target.checked)}
          className="mr-1"
        />
        Allow WhatsApp notifications
      </label>
      <button
        className="bg-blue-600 px-2 py-1 rounded"
        onClick={save}
      >
        Save
      </button>
    </div>
  )
}
