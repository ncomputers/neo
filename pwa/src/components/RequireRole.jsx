import { useAuth } from '../contexts/AuthContext'

export default function RequireRole({ roles, children }) {
  const { user } = useAuth()
  if (!roles.includes(user.role)) {
    return <div>Access denied</div>
  }
  return children
}
