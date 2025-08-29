import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
const App = React.lazy(() => import('./App'))
const Login = React.lazy(() => import('./Login'))
const Dashboard = React.lazy(() => import('./Dashboard'))
const Admin = React.lazy(() => import('./Admin'))
const Troubleshoot = React.lazy(() => import('./Troubleshoot'))
const ProtectedRoute = React.lazy(() => import('./ProtectedRoute'))
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { initRUM } from './rum'

initRUM()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <React.Suspense fallback={<div>Loading...</div>}>
            <App />
          </React.Suspense>
        </ThemeProvider>
      </AuthProvider>
      <Routes>
        <Route
          path="/login"
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <Login />
            </React.Suspense>
          }
        />
        <Route
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <ProtectedRoute
                roles={[
                  'super_admin',
                  'outlet_admin',
                  'manager',
                  'cashier',
                  'kitchen',
                  'cleaner',
                ]}
              />
            </React.Suspense>
          }
        >
          <Route
            path="/"
            element={
              <React.Suspense fallback={<div>Loading...</div>}>
                <App />
              </React.Suspense>
            }
          />
          <Route
            path="/dashboard"
            element={
              <React.Suspense fallback={<div>Loading...</div>}>
                <Dashboard />
              </React.Suspense>
            }
          />
        </Route>
        <Route
          element={
            <React.Suspense fallback={<div>Loading...</div>}>
              <ProtectedRoute
                roles={['super_admin', 'outlet_admin', 'manager']}
              />
            </React.Suspense>
          }
        >
          <Route
            path="/admin"
            element={
              <React.Suspense fallback={<div>Loading...</div>}>
                <Admin />
              </React.Suspense>
            }
          />
          <Route
            path="/admin/troubleshoot"
            element={
              <React.Suspense fallback={<div>Loading...</div>}>
                <Troubleshoot />
              </React.Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js')
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data?.type === 'UPDATE_READY') {
      const banner = document.createElement('div')
      banner.textContent = 'New version available '
      const button = document.createElement('button')
      button.textContent = 'Refresh'
      button.addEventListener('click', () => {
        navigator.serviceWorker.controller?.postMessage('SKIP_WAITING')
        window.location.reload()
      })
      banner.appendChild(button)
      banner.style.position = 'fixed'
      banner.style.bottom = '1rem'
      banner.style.right = '1rem'
      banner.style.padding = '0.5rem 1rem'
      banner.style.background = '#333'
      banner.style.color = '#fff'
      banner.style.borderRadius = '0.25rem'
      banner.style.zIndex = '1000'
      document.body.appendChild(banner)
    }
  })
}
