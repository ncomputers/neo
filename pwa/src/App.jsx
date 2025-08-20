import { Link, Route, Routes } from 'react-router-dom'
import GuestOrder from './pages/GuestOrder'
import AdminDashboard from './pages/AdminDashboard'
import CashierDashboard from './pages/CashierDashboard'
import KitchenDashboard from './pages/KitchenDashboard'
import CleanerDashboard from './pages/CleanerDashboard'
import RequireRole from './components/RequireRole'
import { useAuth } from './contexts/AuthContext'

function Home() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome to the PWA</h1>
      <p className="mt-2">Home route is working.</p>
    </div>
  )
}

export default function App() {
  const { user, loginAs } = useAuth()

  return (
    <div className="p-4">
      <nav className="mb-4 space-x-2">
        <Link to="/">Home</Link>
        <Link to="/guest">Guest</Link>
        <Link to="/admin">Admin</Link>
        <Link to="/cashier">Cashier</Link>
        <Link to="/kitchen">Kitchen</Link>
        <Link to="/cleaner">Cleaner</Link>
        <select
          className="ml-4 border"
          value={user.role}
          onChange={(e) => loginAs(e.target.value)}
        >
          <option value="guest">guest</option>
          <option value="admin">admin</option>
          <option value="cashier">cashier</option>
          <option value="kitchen">kitchen</option>
          <option value="cleaner">cleaner</option>
        </select>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/guest" element={<GuestOrder />} />
        <Route
          path="/admin"
          element={
            <RequireRole roles={['admin']}>
              <AdminDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/cashier"
          element={
            <RequireRole roles={['cashier']}>
              <CashierDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/kitchen"
          element={
            <RequireRole roles={['kitchen']}>
              <KitchenDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/cleaner"
          element={
            <RequireRole roles={['cleaner']}>
              <CleanerDashboard />
            </RequireRole>
          }
        />
      </Routes>
    </div>
  )
}
