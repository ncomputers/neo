import { Outlet } from 'react-router-dom';
import { useLicense } from '@neo/api';
import { LicenseBanner } from '@neo/ui';
import { PoorConnectionBanner } from './PoorConnectionBanner';
import { CookieBanner } from './CookieBanner';

export function Layout() {
  const { data } = useLicense();
  const status = data?.status;
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only">
        Skip to content
      </a>
      <PoorConnectionBanner />
      {status && (
        <LicenseBanner status={status} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
      )}
      <main id="main">
        <Outlet />
      </main>
      <CookieBanner />
    </>
  );
}
