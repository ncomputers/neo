import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Referrals } from './Referrals';
import { getReferral, createReferral, getCredits } from '@neo/api';

vi.mock('@neo/api', () => ({
  getReferral: vi.fn(),
  createReferral: vi.fn(),
  getCredits: vi.fn()
}));

describe('Referrals page', () => {
  beforeEach(() => {
    (getCredits as any).mockResolvedValue({ balance: 0, referrals: 0, adjustments: 0 });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test('shows stats and credit history when referral exists', async () => {
    (getReferral as any).mockResolvedValue({
      code: 'abc',
      landing_url: 'https://ref/abc',
      clicks: 1,
      signups: 2,
      converted: 3,
      max_credit_inr: 5000,
      credits: [
        { id: 'c1', amount_inr: 100, created_at: '2024-01-01', applied_invoice_id: 'inv1' }
      ]
    });
    render(
      <MemoryRouter>
        <Referrals />
      </MemoryRouter>
    );
    await screen.findByDisplayValue('https://ref/abc');
    expect(screen.getByText('Clicks 1')).toBeInTheDocument();
    expect(screen.getByTestId('credits-table').querySelectorAll('tr').length).toBe(2);
  });

  test('generates referral when none exists', async () => {
    (getReferral as any).mockResolvedValue(null);
    (createReferral as any).mockResolvedValue({
      code: 'xyz',
      landing_url: 'https://ref/xyz',
      clicks: 0,
      signups: 0,
      converted: 0,
      max_credit_inr: 5000,
      credits: []
    });
    render(
      <MemoryRouter>
        <Referrals />
      </MemoryRouter>
    );
    const btn = await screen.findByText('Generate Link');
    await userEvent.click(btn);
    await screen.findByDisplayValue('https://ref/xyz');
    expect(createReferral).toHaveBeenCalled();
  });
});
