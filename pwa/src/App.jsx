import React, { Suspense, lazy } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

const RequireRole = lazy(() => import('./components/RequireRole'))
const ConsentBanner = lazy(() => import('./components/ConsentBanner'))
const Loading = lazy(() => import('./components/Loading'))

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
      <Suspense fallback={null}>
        <ConsentBanner />
      </Suspense>
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
      <main id="main-content" role="main">
        <Suspense fallback={<div className="p-4">Loading...</div>}>
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
              path="/admin/onboarding"
              element={
                <RequireRole roles={['admin']}>
                  <OwnerOnboardingWizard />
                </RequireRole>
              }
            />
            <Route
              path="/billing"
              element={
                <RequireRole roles={['admin']}>
                  <Billing />
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
              path="/expo"
              element={
                <RequireRole roles={['cashier']}>
                  <ExpoDashboard />
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
        </Suspense>
      </main>
    </div>
  )
}
