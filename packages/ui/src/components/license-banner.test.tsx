import { render, screen } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { LicenseBanner } from './license-banner';

describe('LicenseBanner', () => {
  test('shows grace message', () => {
    render(<LicenseBanner status="GRACE" daysLeft={3} renewUrl="/r" />);
    expect(screen.getByText(/Subscription ends in 3 days/)).toBeInTheDocument();
    expect(screen.getByText('Renew')).toHaveAttribute('href', '/r');
  });

  test('shows expired message', () => {
    render(<LicenseBanner status="EXPIRED" />);
    expect(screen.getByText('License expired')).toBeInTheDocument();
  });
});
