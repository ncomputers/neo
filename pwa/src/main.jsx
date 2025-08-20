import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import Login from './Login'
import Dashboard from './Dashboard'
import Admin from './Admin'
import ProtectedRoute from './ProtectedRoute'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
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
