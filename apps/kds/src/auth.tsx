import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getToken } from '@neo/api';

function decodeRoles(token?: string): string[] {
  if (!token) return [];
  try {
    const base64 = token.split('.')[1];
    const normalized = base64.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=');
    const payload = JSON.parse(atob(padded));
    return payload.roles || [];
  } catch {
    return [];
  }
}

const AuthContext = createContext<string[]>([]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [roles, setRoles] = useState<string[]>(() => decodeRoles(getToken()?.accessToken));
  useEffect(() => {
    const handler = () => setRoles(decodeRoles(getToken()?.accessToken));
    window.addEventListener('auth', handler);
    return () => window.removeEventListener('auth', handler);
  }, []);
  return <AuthContext.Provider value={roles}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
