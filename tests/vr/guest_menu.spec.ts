import { test, expect } from '@playwright/test';
import fs from 'fs';

const html = `<!DOCTYPE html>
<html>
  <body>
    <div id="menu">
      <h1>Guest Menu</h1>
      <span data-testid="timestamp">12:00</span>
      <ul>
        <li>Item 1</li>
        <li>Item 2</li>
      </ul>
    </div>
  </body>
</html>`;

test('guest menu snapshot', async ({ page }, testInfo) => {
  await page.route('**/guest/menu', route => route.fulfill({
    contentType: 'text/html',
    body: html,
  }));
  await page.goto('/guest/menu');
  const mask = [page.locator('[data-testid="timestamp"]')];
  const snapshot = testInfo.snapshotPath('guest-menu.png');
  if (!fs.existsSync(snapshot)) test.skip('missing baseline snapshot');
  await expect(page).toHaveScreenshot('guest-menu.png', { mask });
});
