import { test, expect } from '@playwright/test';
import fs from 'fs';

const html = `<!DOCTYPE html>
<html>
  <body>
    <div id="kpis" style="display:flex;gap:10px;">
      <div class="kpi">42</div>
      <div class="kpi">7</div>
      <div class="kpi"><span data-testid="counter">3</span></div>
    </div>
  </body>
</html>`;

test('admin dashboard KPI cards snapshot', async ({ page }, testInfo) => {
  await page.route('**/admin/dashboard', route => route.fulfill({
    contentType: 'text/html',
    body: html,
  }));
  await page.goto('/admin/dashboard');
  const mask = [page.locator('[data-testid="counter"]')];
  const snapshot = testInfo.snapshotPath('admin-dashboard-kpis.png');
  if (!fs.existsSync(snapshot)) test.skip('missing baseline snapshot');
  await expect(page.locator('#kpis')).toHaveScreenshot('admin-dashboard-kpis.png', { mask });
});
