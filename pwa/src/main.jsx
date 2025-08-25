import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import App from './App'
import Login from './Login'
import Dashboard from './Dashboard'
import Admin from './Admin'
import ProtectedRoute from './ProtectedRoute'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </AuthProvider>
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
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js')
  navigator.serviceWorker.addEventListener('message', async (event) => {
    if (event.data?.type === 'UPDATE_READY') {
      const reg = await navigator.serviceWorker.getRegistration()
      if (!reg?.waiting) {
        return
      }
      const btn = document.createElement('button')
      btn.textContent = 'New version available'
      btn.style.position = 'fixed'
      btn.style.bottom = '1rem'
      btn.style.right = '1rem'
      btn.style.zIndex = '1000'
      btn.addEventListener('click', async () => {
        await reg.waiting?.skipWaiting()
        window.location.reload()
      })
      document.body.appendChild(btn)
    }
  })
}
