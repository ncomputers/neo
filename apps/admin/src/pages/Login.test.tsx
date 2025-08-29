import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Login } from './Login';
import { useAuth } from '../auth';

describe('Login page', () => {
  beforeEach(() => {
    useAuth.setState({ token: null, roles: [], tenants: [], tenantId: null });
    vi.restoreAllMocks();
  });

  test('shows error when login request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Invalid PIN' })
    }) as any);
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    await userEvent.type(screen.getByPlaceholderText('PIN'), '1');
    await userEvent.click(screen.getByText('Login'));
    await screen.findByRole('alert');
    expect(screen.getByText('Invalid PIN')).toBeInTheDocument();
  });
});
