import { test, expect } from '@playwright/test';
import fs from 'fs';

const html = `<!DOCTYPE html>
<html>
  <body>
    <div id="columns" style="display:flex;gap:10px;">
      <div class="col">A<span data-testid="counter">1</span></div>
      <div class="col">B<span data-testid="counter">2</span></div>
      <div class="col">C<span data-testid="counter">3</span></div>
    </div>
  </body>
</html>`;

test('kds expo columns snapshot', async ({ page }, testInfo) => {
  await page.route('**/kds/expo', route => route.fulfill({
    contentType: 'text/html',
    body: html,
  }));
  await page.goto('/kds/expo');
  const mask = [page.locator('[data-testid="counter"]')];
  const snapshot = testInfo.snapshotPath('kds-expo-columns.png');
  if (!fs.existsSync(snapshot)) test.skip('missing baseline snapshot');
  await expect(page.locator('#columns')).toHaveScreenshot('kds-expo-columns.png', { mask });
});
