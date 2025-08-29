import { test, expect } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const tenant = process.env.TENANT_ID || 'tenant';
const table = process.env.TABLE_CODE || 'T1';

async function placeGuestOrder(page) {
  await page.goto(`${baseURL}/qr?tenant=${tenant}&table=${table}`);
  await page.waitForURL('**/menu');
  await page.getByRole('button', { name: /add/i }).first().click();
  await page.goto(`${baseURL}/cart`);
  await page.getByRole('button', { name: /place order/i }).click();
  await page.waitForURL('**/track/**');
  const match = page.url().match(/\/track\/(\w+)/);
  return match ? match[1] : '';
}

async function kdsProcess(page, orderId) {
  await page.goto(`${baseURL}/kds/expo`);
  await page.getByText(orderId, { exact: false }).first().click();
  await page.getByRole('button', { name: /Accept/i }).click();
  await page.getByRole('button', { name: /Ready/i }).click();
}

async function verifyInvoice(page, orderId) {
  await page.goto(`${baseURL}/track/${orderId}`);
  await page.getByRole('button', { name: /Get bill/i }).click();
  await expect(page.getByText(/invoice/i)).toBeVisible();
}

test('happy path guest/kds/admin', async ({ browser }) => {
  const guestContext = await browser.newContext();
  const guestPage = await guestContext.newPage();
  const orderId = await placeGuestOrder(guestPage);
  expect(orderId).not.toBe('');

  const kdsContext = await browser.newContext();
  const kdsPage = await kdsContext.newPage();
  await kdsProcess(kdsPage, orderId);

  const trackContext = await browser.newContext();
  const trackPage = await trackContext.newPage();
  await verifyInvoice(trackPage, orderId);
});
