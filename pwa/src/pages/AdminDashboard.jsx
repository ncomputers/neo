import { useTheme } from '../contexts/ThemeContext'

export default function AdminDashboard() {
  const { logo } = useTheme()
  return (
    <div className="p-4">
      {logo && <img src={logo} alt="Logo" className="h-16 mb-4" />}
      <h2 className="text-xl font-bold">Admin Dashboard</h2>
    </div>
  )
}
