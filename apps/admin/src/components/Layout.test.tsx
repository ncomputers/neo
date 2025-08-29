import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './Layout';
import { useAuth } from '../auth';

vi.mock('@neo/api', () => ({ useLicenseStatus: () => ({}) }));

describe('Layout', () => {
  beforeEach(() => {
    useAuth.setState({
      token: 't',
      roles: ['manager'],
      tenants: [{ id: '1', name: 'A' }],
      tenantId: '1'
    });
  });

  test('managers do not see Billing link', () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<Layout />}>
            <Route index element={<div />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
    expect(screen.queryByText('Billing')).toBeNull();
  });
});
