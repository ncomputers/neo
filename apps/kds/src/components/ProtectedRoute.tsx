import { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getToken, useLicense } from '@neo/api';
import { LicenseBanner } from '@neo/ui';
import { useAuth } from '../auth';

interface Props {
  roles?: string[];
  children: ReactElement;
}

export function ProtectedRoute({ roles, children }: Props) {
  const userRoles = useAuth();
  const location = useLocation();
  const { data } = useLicense();
  const status = data?.status;
  if (!getToken()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.some((r) => userRoles.includes(r))) {
    return <h1>403</h1>;
  }
  return (
    <>
      {status && status !== 'ACTIVE' && (
        <LicenseBanner status={status as 'GRACE' | 'EXPIRED'} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
      )}
      {children}
    </>
  );
}
