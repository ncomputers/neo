import { Navigate, Outlet } from 'react-router-dom'

export default function ProtectedRoute({ roles }) {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  if (roles && !roles.includes(role)) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
