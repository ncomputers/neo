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

