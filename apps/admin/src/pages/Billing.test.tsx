import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Billing } from './Billing';
import {
  getBillingPlan,
  previewBillingPlan,
  changeBillingPlan
} from '@neo/api';

vi.mock('@neo/api', () => ({
  getBillingPlan: vi.fn(),
  previewBillingPlan: vi.fn(),
  changeBillingPlan: vi.fn()
}));

describe('Billing page', () => {
  beforeEach(() => {
    (getBillingPlan as any).mockResolvedValue({
      plan_id: 'starter',
      active_tables: 2
    });
    (previewBillingPlan as any).mockResolvedValue({
      delta: 100,
      gst: 18,
      table_cap: 5,
      effective: '2023-01-01T00:00:00Z'
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  test('Preview renders Δ₹ and GST lines', async () => {
    render(<Billing />);
    await userEvent.click(screen.getByText('Change Plan'));
    await userEvent.click(screen.getByText('Pro'));
    await screen.findByText('Δ₹100');
    expect(screen.getByText('GST ₹18')).toBeInTheDocument();
  });

  test('Upgrade now posts and shows invoice link', async () => {
    (changeBillingPlan as any).mockResolvedValue({ invoice_id: 'inv1' });
    render(<Billing />);
    await userEvent.click(screen.getByText('Change Plan'));
    await userEvent.click(screen.getByText('Pro'));
    await userEvent.click(screen.getByText('Upgrade now'));
    const link = await screen.findByTestId('invoice-link');
    expect(link).toHaveAttribute('href', '/invoice/inv1/pdf');
    expect(changeBillingPlan).toHaveBeenCalledWith({
      to_plan_id: 'pro',
      change_type: 'upgrade',
      when: 'now'
    });
  });

  test('Downgrade schedules and renders chip', async () => {
    (previewBillingPlan as any).mockResolvedValue({
      delta: -50,
      gst: -9,
      table_cap: 1,
      effective: '2023-01-01T00:00:00Z'
    });
    (changeBillingPlan as any).mockResolvedValue({
      scheduled_for: '2024-05-01T00:00:00Z'
    });
    render(<Billing />);
    await userEvent.click(screen.getByText('Change Plan'));
    await userEvent.click(screen.getByText('Starter'));
    await userEvent.click(screen.getByText('Schedule downgrade'));
    const chip = await screen.findByTestId('schedule-chip');
    expect(chip.textContent).toContain('Scheduled for');
    expect(changeBillingPlan).toHaveBeenCalledWith({
      to_plan_id: 'starter',
      change_type: 'downgrade',
      when: 'period_end'
    });
  });
});

