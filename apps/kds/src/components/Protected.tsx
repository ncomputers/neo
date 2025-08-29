import { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getToken } from '@neo/api';
import { useAuth } from '../auth';

interface Props {
  roles?: string[];
  children: ReactElement;
}

export function Protected({ roles, children }: Props) {
  const userRoles = useAuth();
  const location = useLocation();
  if (!getToken()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.some((r) => userRoles.includes(r))) {
    return <Navigate to="/" replace />;
  }
  return children;
}
