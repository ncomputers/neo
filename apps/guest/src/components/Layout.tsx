import { Outlet } from 'react-router-dom';
import { useLicense } from '@neo/api';
import { LicenseBanner } from '@neo/ui';
import { ConnectionBanner } from './ConnectionBanner';

export function Layout() {
  const { data } = useLicense();
  const status = data?.status;
  return (
    <div>
      <ConnectionBanner />
      {status && (
        <LicenseBanner status={status} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
      )}
      <Outlet />
    </div>
  );
}
