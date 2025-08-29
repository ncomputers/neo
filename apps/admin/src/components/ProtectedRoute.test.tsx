import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import * as api from '@neo/api';

describe('ProtectedRoute', () => {
  test('redirects to login without token', () => {
    vi.spyOn(api, 'getToken').mockReturnValue(null as any);
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<ProtectedRoute><div>home</div></ProtectedRoute>} />
          <Route path="/login" element={<div>login</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('login')).toBeInTheDocument();
  });
});
