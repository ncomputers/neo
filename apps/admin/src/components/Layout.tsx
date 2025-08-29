import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from '../auth';
import { clearToken, useLicense, useVersion } from '@neo/api';
import { LicenseBanner, toast } from '@neo/ui';
import pkg from '../../package.json';

export function Layout() {
  const roles = useAuth();
  const navigate = useNavigate();
  const { data } = useLicense();
  const { data: api } = useVersion();
  const status = data?.status;
  const uiVersion = pkg.version;

  useEffect(() => {
    const seen = localStorage.getItem('uiVersion');
    if (seen !== uiVersion) {
      toast("What's new", {
        action: {
          label: 'View',
          onClick: () => navigate('/changelog'),
        },
      });
      localStorage.setItem('uiVersion', uiVersion);
    }
  }, [navigate, uiVersion]);
  return (
    <div className="flex h-screen">
      <a href="#main" className="sr-only focus:not-sr-only">
        Skip to content
      </a>
      <aside className="w-48 bg-gray-100 p-4 space-y-2">
        <nav className="flex flex-col space-y-2" aria-label="Primary">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/floor">Floor</Link>
          {roles.includes('owner') && <Link to="/billing">Billing</Link>}
          <Link to="/onboarding">Onboarding</Link>
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        {status && (
          <LicenseBanner status={status} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
        )}
          <header className="flex justify-between items-center p-2 border-b">
            <div className="flex items-center space-x-2">
              <div
                className="h-8 w-24 bg-contain bg-no-repeat"
                style={{ backgroundImage: 'var(--logo-url)' }}
              />
            </div>
            <div className="flex items-center space-x-4">
              <Link to="/support">Help</Link>
              <button
                onClick={() => {
                  clearToken();
                  navigate('/login');
                }}
              >
                Logout
              </button>
            </div>
          </header>
        <main id="main" className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
        <footer className="p-2 border-t text-xs flex justify-between">
          <span>UI v{uiVersion}</span>
          <span>API {api?.sha?.slice(0,7) ?? 'unknown'}</span>
        </footer>
      </div>
    </div>
  );
}
