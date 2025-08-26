import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import App from './App'
import Login from './Login'
import Dashboard from './Dashboard'
import Admin from './Admin'
import Troubleshoot from './Troubleshoot'
import ProtectedRoute from './ProtectedRoute'
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
          <Route path="/admin/troubleshoot" element={<Troubleshoot />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js')
}
