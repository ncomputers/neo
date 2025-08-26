import { test, expect } from '@playwright/test';

// End-to-end flow ensuring expo hotkey picks orders
// Assumes API server available at baseURL and tenant resolved via headers

test('expo ticket is picked via hotkey', async ({ page, request }) => {
  // Place an order and mark it ready
  const orderResp = await request.post('/api/outlet/demo/guest/order', {
    data: {
      table: '1',
      items: [{ sku: 'coffee', qty: 1 }],
    },
  });
  const order = await orderResp.json();
  await request.post(`/api/outlet/demo/kds/order/${order.id}/ready`);

  // Open expo view and ensure ticket visible
  await page.goto('/kds/expo', { waitUntil: 'networkidle' });
  const ticket = page.getByText(`Table ${order.table}`);
  await expect(ticket).toBeVisible();
  await expect(ticket.locator('..').locator('text=m')).not.toHaveText('0m');

  // Pick via hotkey and wait for API
  const picked = page.waitForResponse(
    (resp) => resp.url().includes(`/kds/expo/${order.id}/picked`) && resp.request().method() === 'POST'
  );
  await page.keyboard.press('P');
  await picked;

  await expect(ticket).toHaveCount(0);

  // Audit should record expo.picked
  const audit = await request.get('/api/admin/audit/logs');
  const auditData = await audit.json();
  expect(auditData.data.find((e: any) => e.action === 'expo.picked' && e.meta.order_id === order.id)).toBeTruthy();
});
