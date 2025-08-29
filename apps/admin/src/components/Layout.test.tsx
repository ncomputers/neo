import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './Layout';

vi.mock('@neo/api', () => ({
  clearToken: vi.fn(),
  useLicense: () => ({ data: { status: 'GRACE', daysLeft: 2, renewUrl: '/billing' } }),
  useVersion: () => ({ data: { sha: 'abc1234' } })
}));

vi.mock('../auth', () => ({ useAuth: () => [] }));

describe('Layout', () => {
  test('shows grace banner', () => {
    render(
      <MemoryRouter initialEntries={['/']}> 
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<div>home</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Subscription ends in 2 days/)).toBeInTheDocument();
  });
});
