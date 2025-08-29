import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { clearToken, useLicense } from '@neo/api';
import { LicenseBanner } from '@neo/ui';

export function Layout() {
  const roles = useAuth();
  const navigate = useNavigate();
  const { data } = useLicense();
  const status = data?.status;
  return (
    <div className="flex h-screen">
      <aside className="w-48 bg-gray-100 p-4 space-y-2">
        <nav className="flex flex-col space-y-2">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/floor">Floor</Link>
          {roles.includes('owner') && <Link to="/billing">Billing</Link>}
          <Link to="/onboarding">Onboarding</Link>
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        {status && status !== 'ACTIVE' && (
          <LicenseBanner status={status as 'GRACE' | 'EXPIRED'} daysLeft={data?.daysLeft} renewUrl={data?.renewUrl} />
        )}
        <header className="flex justify-between items-center p-2 border-b">
          <div className="flex items-center space-x-2">
            <div
              className="h-8 w-24 bg-contain bg-no-repeat"
              style={{ backgroundImage: 'var(--logo-url)' }}
            />
          </div>
          <button
            onClick={() => {
              clearToken();
              navigate('/login');
            }}
          >
            Logout
          </button>
        </header>
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
