import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { useLicenseStatus } from '@neo/api';
import { LicenseBanner } from '@neo/ui';

export function Layout() {
  const { tenants, tenantId, setTenant, logout, roles } = useAuth();
  const navigate = useNavigate();
  const current = tenants.find((t) => t.id === tenantId);
  const { data: license } = useLicenseStatus();
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
        <LicenseBanner status={license?.status} daysLeft={license?.days_left} renewUrl={license?.renew_url} />
        <header className="flex justify-between items-center p-2 border-b">
          <div className="flex items-center space-x-2">
            <div
              className="h-8 w-24 bg-contain bg-no-repeat"
              style={{ backgroundImage: 'var(--logo-url)' }}
            />
            {tenants.length > 1 ? (
              <select
                value={tenantId ?? undefined}
                onChange={(e) => setTenant(e.target.value)}
              >
                {tenants.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            ) : (
              <span>{current?.name}</span>
            )}
          </div>
          <button
            onClick={() => {
              logout();
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
