import { Outlet } from 'react-router-dom';
import { useLicense } from '@neo/api';
import { LicenseBanner } from '@neo/ui';

export function Layout() {
  const { data } = useLicense();
  const status = data?.status;
  return (
    <div>
      {status && status !== 'ACTIVE' && (
        <LicenseBanner status={status as 'GRACE' | 'EXPIRED'} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
      )}
      <Outlet />
    </div>
  );
}
