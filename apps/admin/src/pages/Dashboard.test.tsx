import { describe, test, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { Dashboard } from './Dashboard';
import { useAuth } from '../auth';

const sources: any[] = [];
class MockEventSource {
  onmessage: ((ev: any) => void) | null = null;
  onopen: ((ev: any) => void) | null = null;
  constructor(public url: string) {
    sources.push(this);
    setTimeout(() => this.onopen?.({}), 0);
  }
  close() {}
}

beforeEach(() => {
  (global as any).EventSource = MockEventSource as any;
  useAuth.setState({
    token: 't',
    roles: ['owner'],
    tenants: [{ id: '1', name: 'A' }],
    tenantId: '1'
  });
});

afterEach(() => {
  cleanup();
  sources.length = 0;
});

describe('Dashboard', () => {
  test('SSE updates KPI values', async () => {
    render(<Dashboard />);
    const es = sources[0];
    es.onmessage?.({
      data: JSON.stringify({
        orders_today: 5,
        sales: 123,
        prep_p50: 10,
        eta_sla_pct: 90,
        webhook_breaker_pct: 2
      })
    });
    await screen.findByText('Orders Today: 5');
    screen.getByText('Sales ₹: 123');
  });
});
