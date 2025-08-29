import { test, expect } from '@playwright/test';

const guestBaseURL = process.env.GUEST_BASE_URL || process.env.BASE_URL || 'http://localhost:3000';

// Visual regression for guest menu screen
// Masks dynamic timestamps and counters

test('guest menu snapshot', async ({ page }) => {
  await page.goto(`${guestBaseURL}/guest/menu`, { waitUntil: 'networkidle' });
  const mask = [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="counter"]'),
  ];
  const screenshot = await page.screenshot({ mask });
  expect(screenshot).toMatchSnapshot('guest-menu.png');
});
