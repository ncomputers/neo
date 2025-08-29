import { Outlet } from 'react-router-dom';
import { useLicenseStatus } from '@neo/api';
import { LicenseBanner } from '@neo/ui';

export function Layout() {
  const { data } = useLicenseStatus();
  return (
    <div>
      <LicenseBanner status={data?.status} daysLeft={data?.days_left} renewUrl={data?.renew_url} />
      <Outlet />
    </div>
  );
}
