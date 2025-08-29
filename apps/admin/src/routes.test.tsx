import { describe, test, expect, beforeEach, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { render, waitFor, cleanup } from '@testing-library/react';
import { routes } from './routes';
import { useAuth } from './auth';
import { afterEach } from 'vitest';

vi.mock('@neo/api', () => ({ useLicenseStatus: () => ({}) }), { virtual: true });

const ES = global.EventSource;

beforeEach(() => {
  cleanup();
  useAuth.setState({ token: null, roles: [], tenants: [], tenantId: null });
  (global as any).EventSource = class {
    onmessage: any = null;
    onopen: any = null;
    close() {}
  };
});

afterEach(() => {
  (global as any).EventSource = ES;
});

describe('route guards', () => {
  test('blocks non-owners from /billing', async () => {
    useAuth.setState({
      token: 't',
      roles: ['manager'],
      tenants: [{ id: '1', name: 'A' }],
      tenantId: '1'
    });
    const router = createMemoryRouter(routes, { initialEntries: ['/billing'] });
    render(<RouterProvider router={router} />);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/dashboard');
    });
  });
});
