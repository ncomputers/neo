import { useTheme } from '../contexts/ThemeContext'

export default function CashierDashboard() {
  const { logo } = useTheme()
  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold">Cashier Dashboard</h2>
    </div>
  )
}
