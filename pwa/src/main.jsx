import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { initRUM } from './rum'

const App = lazy(() => import('./App'))
const Login = lazy(() => import('./Login'))
const Dashboard = lazy(() => import('./Dashboard'))
const Admin = lazy(() => import('./Admin'))
const Troubleshoot = lazy(() => import('./Troubleshoot'))
const ProtectedRoute = lazy(() => import('./ProtectedRoute'))

initRUM()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <Suspense fallback={<div>Loading...</div>}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                element={
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
                }
              >
                <Route path="/" element={<App />} />
                <Route path="/dashboard" element={<Dashboard />} />
              </Route>
              <Route
                element={
                  <ProtectedRoute
                    roles={['super_admin', 'outlet_admin', 'manager']}
                  />
                }
              >
                <Route path="/admin" element={<Admin />} />
                <Route path="/admin/troubleshoot" element={<Troubleshoot />} />
              </Route>
            </Routes>
          </Suspense>
        </ThemeProvider>
      </AuthProvider>
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
