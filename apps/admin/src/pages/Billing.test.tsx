import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, cleanup, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Billing } from './Billing';
import {
  listInvoices,
  downloadInvoice,
  getCredits,
  getSubscription,
  previewBillingPlan,
  changeBillingPlan
} from '@neo/api';

vi.mock('@neo/api', () => ({
  listInvoices: vi.fn(),
  downloadInvoice: vi.fn(),
  getCredits: vi.fn(),
  getSubscription: vi.fn(),
  previewBillingPlan: vi.fn(),
  changeBillingPlan: vi.fn()
}));

describe('Billing page', () => {
  beforeEach(() => {
    (getCredits as any).mockResolvedValue({
      balance: 0,
      referrals: 0,
      adjustments: 0
    });
    (getSubscription as any).mockResolvedValue({
      plan_id: 'starter',
      table_cap: 5,
      active_tables: 1,
      status: 'ACTIVE',
      current_period_end: '2099-01-01T00:00:00Z'
    });
    (listInvoices as any).mockResolvedValue([
      {
        id: 'inv1',
        date: '2024-01-01',
        number: '1',
        period: { from: '2024-01-01', to: '2024-01-31' },
        amount: 100,
        gst: 18,
        status: 'PAID'
      },
      {
        id: 'inv2',
        date: '2024-02-01',
        number: '2',
        period: { from: '2024-02-01', to: '2024-02-28' },
        amount: 100,
        gst: 18,
        status: 'OPEN'
      }
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test('Filters change query params and table rows', async () => {
    render(
      <MemoryRouter>
        <Billing />
      </MemoryRouter>
    );
    await screen.findByTestId('download-inv1');
    expect(screen.getAllByRole('row')).toHaveLength(3);

    (listInvoices as any).mockResolvedValueOnce([
      {
        id: 'inv2',
        date: '2024-02-01',
        number: '2',
        period: { from: '2024-02-01', to: '2024-02-28' },
        amount: 100,
        gst: 18,
        status: 'OPEN'
      }
    ]);
    await userEvent.selectOptions(screen.getByTestId('status-filter'), 'OPEN');
    const table = screen.getByTestId('invoice-table');
    await within(table).findByText('OPEN');
    expect(listInvoices).toHaveBeenLastCalledWith({ from: '', to: '', status: 'OPEN' });
    expect(screen.getAllByRole('row')).toHaveLength(2);
    expect(screen.getByTestId('csv-export')).toHaveAttribute(
      'href',
      '/admin/billing/invoices.csv?status=OPEN'
    );
  });

  test('PDF download called with right id', async () => {
    render(
      <MemoryRouter>
        <Billing />
      </MemoryRouter>
    );
    const btn = await screen.findByTestId('download-inv1');
    await userEvent.click(btn);
    expect(downloadInvoice).toHaveBeenCalledWith('inv1');
  });

  test('Plan & Usage shows credits and status chips', async () => {
    (getCredits as any).mockResolvedValueOnce({
      balance: 50,
      referrals: 20,
      adjustments: 30
    });
    (getSubscription as any).mockResolvedValueOnce({
      plan_id: 'starter',
      table_cap: 5,
      active_tables: 6,
      status: 'ACTIVE',
      current_period_end: '2099-01-01T00:00:00Z',
      scheduled_change: { to_plan_id: 'starter', scheduled_for: '2099-02-01T00:00:00Z' }
    });

    render(
      <MemoryRouter>
        <Billing />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByText('Plan & Usage'));
    await screen.findByText('Credits ₹50');
    expect(screen.getByText('Tables 6/5')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-chip')).toBeInTheDocument();
    expect(screen.getByTestId('overcap-chip')).toBeInTheDocument();
  });

  test('GRACE banner renders with CTA', async () => {
    (getSubscription as any).mockResolvedValueOnce({
      plan_id: 'starter',
      table_cap: 5,
      active_tables: 1,
      status: 'GRACE',
      current_period_end: '2024-01-01T00:00:00Z',
      grace_ends_at: '2099-01-01T00:00:00Z'
    });
    render(
      <MemoryRouter>
        <Billing />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByText('Plan & Usage'));
    await screen.findByText(/Subscription in grace period/);
    expect(screen.getByText('Renew now')).toBeInTheDocument();
  });

  test('EXPIRED banner renders with CTA', async () => {
    (getSubscription as any).mockResolvedValueOnce({
      plan_id: 'starter',
      table_cap: 5,
      active_tables: 1,
      status: 'EXPIRED',
      current_period_end: '2024-01-01T00:00:00Z'
    });
    render(
      <MemoryRouter>
        <Billing />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByText('Plan & Usage'));
    await screen.findByText(/Subscription expired/);
    expect(screen.getByText('Renew now')).toBeInTheDocument();
  });
});

