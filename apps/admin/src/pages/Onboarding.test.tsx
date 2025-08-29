import { beforeEach, describe, expect, test, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Onboarding } from './Onboarding';

describe('Onboarding wizard', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
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
    await userEvent.click(screen.getByText('Next'));
    const input = screen.getByLabelText('Table Count');
    await userEvent.type(input, '5');
    const saved = JSON.parse(localStorage.getItem('onboarding') as string);
    expect(saved.tables.count).toBe(5);
  });

  test('downloads QR ZIP', async () => {
    const originalFetch = global.fetch;
    const fetchMock = vi.fn().mockResolvedValue({ blob: vi.fn().mockResolvedValue(new Blob()) });
    // @ts-ignore
    global.fetch = fetchMock;
    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
        </Routes>
      </MemoryRouter>
    );
    await userEvent.click(screen.getByText('Next'));
    await userEvent.click(screen.getByText('Next'));
    await userEvent.click(screen.getByText('Download QR ZIP'));
    expect(fetchMock).toHaveBeenCalled();
    global.fetch = originalFetch;
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

