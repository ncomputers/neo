import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

export function Layout() {
  const { tenants, tenantId, setTenant, logout } = useAuth();
  const navigate = useNavigate();
  const current = tenants.find((t) => t.id === tenantId);
  return (
    <div className="flex h-screen">
      <aside className="w-48 bg-gray-100 p-4 space-y-2">
        <nav className="flex flex-col space-y-2">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/floor">Floor</Link>
          <Link to="/billing">Billing</Link>
          <Link to="/onboarding">Onboarding</Link>
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="flex justify-between items-center p-2 border-b">
          <div>
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
