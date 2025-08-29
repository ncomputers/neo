import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Login } from './Login';
import { loginPin } from '@neo/api';

vi.mock('@neo/api', () => ({ loginPin: vi.fn() }));

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows error when login request fails', async () => {
    (loginPin as any).mockRejectedValue(new Error('Invalid PIN'));
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
