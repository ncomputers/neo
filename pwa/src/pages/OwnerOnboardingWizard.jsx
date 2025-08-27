import { useEffect, useState } from 'react'

const STEPS = [
  { id: 'brand', title: 'Brand & Logo' },
  { id: 'tables', title: 'Tables Count' },
  { id: 'menu', title: 'Menu Import' },
  { id: 'printer', title: 'Printer Test' },
  { id: 'payments', title: 'Payment Mode' },
  { id: 'alerts', title: 'Alerts Rules' },
]

const STORAGE_KEY = 'owner_onboarding_progress'

export default function OwnerOnboardingWizard() {
  const [step, setStep] = useState(0)
  const [data, setData] = useState({})

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setStep(parsed.step || 0)
        setData(parsed.data || {})
      } catch {
        // ignore parse errors
      }
    }
  }, [])

  function persist(nextStep, nextData) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ step: nextStep, data: nextData })
    )
  }

  const current = STEPS[step]

  function handleNext(e) {
    e.preventDefault()
    const formData = new FormData(e.target)
    const currentData = {}
    formData.forEach((value, key) => {
      currentData[key] = value
    })
    const nextData = { ...data, [current.id]: currentData }
    const nextStep = step + 1
    if (nextStep >= STEPS.length) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      persist(nextStep, nextData)
    }
    setData(nextData)
    setStep(nextStep)
  }

  if (step >= STEPS.length) {
    return (
      <div className="p-4">
        <h2 className="text-xl font-bold mb-4">Onboarding Complete</h2>
        <p className="mb-4">You're ready to go live.</p>
        <a href="/help/owner_onboarding" className="text-blue-600 underline">
          Launch checklist
        </a>
      </div>
    )
  }

  function renderStep() {
    switch (current.id) {
      case 'brand':
        return (
          <>
            <label className="block mb-2">
              Brand Name
              <input name="name" className="border ml-2" />
            </label>
            <label className="block mb-4">
              Logo URL
              <input name="logo" className="border ml-2" />
            </label>
          </>
        )
      case 'tables':
        return (
          <label className="block mb-4">
            Number of Tables
            <input name="count" type="number" min="1" className="border ml-2" />
          </label>
        )
      case 'menu':
        return (
          <label className="block mb-4">
            Import Menu
            <input name="file" type="file" className="border ml-2" />
          </label>
        )
      case 'printer':
        return (
          <p className="mb-4">
            Send a test print from your browser and verify the receipt before
            proceeding.
          </p>
        )
      case 'payments':
        return (
          <label className="block mb-4">
            Payment Mode
            <select name="mode" className="border ml-2">
              <option value="upi">UPI</option>
              <option value="cash">Cash</option>
            </select>
          </label>
        )
      case 'alerts':
        return (
          <label className="block mb-4">
            Alert Rules
            <textarea name="rules" className="border ml-2" />
          </label>
        )
      default:
        return null
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">
        Step {step + 1} of {STEPS.length}: {current.title}
      </h2>
      <form onSubmit={handleNext}>
        {renderStep()}
        <button type="submit" className="bg-blue-600 text-white px-4 py-2">
          Next
        </button>
      </form>
    </div>
  )
}
