import { create } from 'zustand';

interface Tenant { id: string; name: string }

interface AuthState {
  token: string | null;
  roles: string[];
  tenants: Tenant[];
  tenantId: string | null;
  login: (pin: string) => Promise<void>;
  logout: () => void;
  setTenant: (id: string) => void;
}

function decodeToken(token: string) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload;
  } catch {
    return {};
  }
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  roles: [],
  tenants: [],
  tenantId: null,
  async login(pin: string) {
    const res = await fetch('/admin/login-pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin })
    });
    const { token } = await res.json();
    sessionStorage.setItem('token', token);
    const payload = decodeToken(token);
    const roles: string[] = payload.roles || [];
    const tenants: Tenant[] = payload.tenants || [];
    let tenantId = localStorage.getItem('tenantId') || tenants[0]?.id || null;
    if (tenantId) localStorage.setItem('tenantId', tenantId);
    set({ token, roles, tenants, tenantId });
  },
  logout() {
    sessionStorage.removeItem('token');
    set({ token: null, roles: [], tenants: [], tenantId: null });
  },
  setTenant(id: string) {
    localStorage.setItem('tenantId', id);
    set({ tenantId: id });
  }
}));

if (typeof window !== 'undefined') {
  const token = sessionStorage.getItem('token');
  if (token) {
    const payload = decodeToken(token);
    const roles: string[] = payload.roles || [];
    const tenants: Tenant[] = payload.tenants || [];
    const tenantId = localStorage.getItem('tenantId') || tenants[0]?.id || null;
    useAuth.setState({ token, roles, tenants, tenantId });
  }
}
