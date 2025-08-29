import { test, expect } from '@playwright/test';

const kdsBaseURL = process.env.KDS_BASE_URL || process.env.BASE_URL || 'http://localhost:3000';

// Visual regression for KDS expo columns with mocked tickets
// Masks dynamic timestamps and counters

test('kds expo snapshot', async ({ page }) => {
  await page.route('**/tickets**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ tickets: [{ id: 1, item: 'Mock item' }] }),
    });
  });
  await page.goto(`${kdsBaseURL}/kds/expo`);
  const columns = page.locator('[data-testid="kds-columns"]');
  const mask = [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="counter"]'),
  ];
  const screenshot = await columns.screenshot({ mask });
  expect(screenshot).toMatchSnapshot('kds-expo.png');
});
