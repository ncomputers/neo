import { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

interface Props {
  roles?: string[];
  children: ReactElement;
}

export function ProtectedRoute({ roles, children }: Props) {
  const { token, roles: userRoles } = useAuth();
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.some((r) => userRoles.includes(r))) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
