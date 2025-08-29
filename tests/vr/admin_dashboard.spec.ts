import { test, expect } from '@playwright/test';

const adminBaseURL = process.env.ADMIN_BASE_URL || process.env.BASE_URL || 'http://localhost:3000';

// Visual regression for admin dashboard KPI cards with mocked SSE
// Masks dynamic timestamps and counters

test('admin dashboard snapshot', async ({ page }) => {
  await page.route('**/sse/**', route => {
    route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: 'data: {"kpi": 42}\n\n',
    });
  });
  await page.goto(`${adminBaseURL}/admin/dashboard`, { waitUntil: 'networkidle' });
  const kpis = page.locator('[data-testid="kpi-cards"]');
  const mask = [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="counter"]'),
  ];
  const screenshot = await kpis.screenshot({ mask });
  expect(screenshot).toMatchSnapshot('admin-dashboard.png');
});
