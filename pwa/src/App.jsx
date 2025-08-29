import React from 'react'
import { Link, Route, Routes } from 'react-router-dom'
const GuestOrder = React.lazy(() => import('./pages/GuestOrder'))
const AdminDashboard = React.lazy(() => import('./pages/AdminDashboard'))
const CashierDashboard = React.lazy(() => import('./pages/CashierDashboard'))
const KitchenDashboard = React.lazy(() => import('./pages/KitchenDashboard'))
const CleanerDashboard = React.lazy(() => import('./pages/CleanerDashboard'))
const Billing = React.lazy(() => import('./pages/Billing'))
const ExpoDashboard = React.lazy(() => import('./pages/ExpoDashboard'))
const OwnerOnboardingWizard = React.lazy(
  () => import('./pages/OwnerOnboardingWizard'),
)
const RequireRole = React.lazy(() => import('./components/RequireRole'))
const ConsentBanner = React.lazy(() => import('./components/ConsentBanner'))
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
    <main id="main-content" role="main" className="p-4">
      <React.Suspense fallback={<div>Loading...</div>}>
        <ConsentBanner />
      </React.Suspense>
      <nav aria-label="Primary" className="mb-4 space-x-2">
        <Link to="/">Home</Link>
        <Link to="/guest">Guest</Link>
        <Link to="/admin">Admin</Link>
        <Link to="/billing">Billing</Link>
        {user.role === 'admin' && (
          <a href="/help" target="_blank" rel="noopener noreferrer">
            Help Center
          </a>
        )}
        <Link to="/cashier">Cashier</Link>
        <Link to="/expo">Expo</Link>
        <Link to="/kitchen">Kitchen</Link>
        <Link to="/cleaner">Cleaner</Link>
        <label htmlFor="role-select" className="sr-only">
          Role
        </label>
        <select
          id="role-select"
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
        <Route
          path="/guest"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <GuestOrder />
            </React.Suspense>
          }
        />
        <Route
          path="/admin"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['admin']}>
                <AdminDashboard />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/admin/onboarding"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['admin']}>
                <OwnerOnboardingWizard />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/billing"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['admin']}>
                <Billing />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/cashier"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['cashier']}>
                <CashierDashboard />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/expo"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['cashier']}>
                <ExpoDashboard />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/kitchen"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['kitchen']}>
                <KitchenDashboard />
              </RequireRole>
            </React.Suspense>
          }
        />
        <Route
          path="/cleaner"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <RequireRole roles={['cleaner']}>
                <CleanerDashboard />
              </RequireRole>
            </React.Suspense>
          }
        />
      </Routes>
    </main>
  )
}
