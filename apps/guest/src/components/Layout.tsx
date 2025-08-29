import { Outlet } from 'react-router-dom';
import { useLicense } from '@neo/api';
import { LicenseBanner, CookieBanner } from '@neo/ui';
import { PoorConnectionBanner } from './PoorConnectionBanner';
import { enableAnalytics, disableAnalytics } from '../analytics';
import { capturePageView } from '@neo/utils';

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
      <main id="main" role="main" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="p-4 text-center text-xs flex justify-center gap-4">
        <a href="/privacy" className="underline">Privacy</a>
        <a href="/terms" className="underline">Terms</a>
      </footer>
      <CookieBanner
        onAccept={() => {
          enableAnalytics();
          capturePageView(window.location.pathname);
        }}
        onDecline={disableAnalytics}
      />
    </>
  );
}
