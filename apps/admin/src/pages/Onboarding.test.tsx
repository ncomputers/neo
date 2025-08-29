import { beforeEach, describe, expect, test } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Onboarding } from './Onboarding';

describe('Onboarding wizard', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('saves table count to localStorage', async () => {
    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
        </Routes>
      </MemoryRouter>
    );
    await userEvent.click(screen.getByText('Next'));
    const input = screen.getByLabelText('Table Count');
    await userEvent.type(input, '5');
    const saved = JSON.parse(localStorage.getItem('onboarding') as string);
    expect(saved.tables.count).toBe(5);
  });

  test('redirects to dashboard when completed', () => {
    localStorage.setItem('onboarding_completed', 'true');
    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<div>dash</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('dash')).toBeInTheDocument();
  });
});

