import { test, expect } from '@playwright/test';

test('guest to cashier full flow', async ({ page }) => {
  await page.setContent(`
    <button id="filter-veg">Filter Veg</button>
    <button id="add-pizza" data-category="veg" style="display:none;">Add Pizza - $10</button>
    <button id="place-order">Place Order</button>
    <div id="status"></div>
    <button id="kds-accept" style="display:none;">KDS Accept</button>
    <button id="prep-done" style="display:none;">Prep Done</button>
    <button id="deliver" style="display:none;">Deliver</button>
    <button id="add-drink" style="display:none;">Add Drink - $5</button>
    <button id="generate-bill" style="display:none;">Generate Bill</button>
    <div id="bill"></div>
    <button id="pay-split" style="display:none;">Split Pay</button>
    <button id="mark-paid" style="display:none;">Mark Paid</button>
    <button id="soft-delete-item" style="display:none;">Soft Delete Item</button>
    <button id="soft-delete-table" style="display:none;">Soft Delete Table</button>
    <script>
      let cart = [];
      document.getElementById('filter-veg').addEventListener('click', () => {
        document.getElementById('add-pizza').style.display = 'block';
      });
      document.getElementById('add-pizza').addEventListener('click', () => {
        cart.push('pizza');
      });
      document.getElementById('place-order').addEventListener('click', () => {
        document.getElementById('status').textContent = 'order placed';
        document.getElementById('kds-accept').style.display = 'block';
      });
      document.getElementById('kds-accept').addEventListener('click', () => {
        document.getElementById('status').textContent = 'accepted';
        document.getElementById('prep-done').style.display = 'block';
      });
      document.getElementById('prep-done').addEventListener('click', () => {
        document.getElementById('status').textContent = 'ready';
        document.getElementById('deliver').style.display = 'block';
      });
      document.getElementById('deliver').addEventListener('click', () => {
        document.getElementById('status').textContent = 'delivered';
        document.getElementById('add-drink').style.display = 'block';
      });
      document.getElementById('add-drink').addEventListener('click', () => {
        cart.push('drink');
        document.getElementById('generate-bill').style.display = 'block';
      });
      document.getElementById('generate-bill').addEventListener('click', () => {
        document.getElementById('bill').textContent = 'Bill for ' + cart.length + ' items';
        document.getElementById('pay-split').style.display = 'block';
      });
      document.getElementById('pay-split').addEventListener('click', () => {
        document.getElementById('bill').textContent = 'Split payment';
        document.getElementById('mark-paid').style.display = 'block';
      });
      document.getElementById('mark-paid').addEventListener('click', () => {
        document.getElementById('bill').textContent = 'Paid';
        document.getElementById('soft-delete-item').style.display = 'block';
        document.getElementById('soft-delete-table').style.display = 'block';
      });
      document.getElementById('soft-delete-item').addEventListener('click', () => {
        document.getElementById('add-pizza').dataset.deleted = 'true';
      });
      document.getElementById('soft-delete-table').addEventListener('click', () => {
        document.getElementById('place-order').dataset.deleted = 'true';
      });
    <\/script>
  `);

  await page.click('#filter-veg');
  await page.click('#add-pizza');
  await page.click('#place-order');
  await expect(page.locator('#status')).toHaveText('order placed');

  await page.click('#kds-accept');
  await expect(page.locator('#status')).toHaveText('accepted');

  await page.click('#prep-done');
  await page.click('#deliver');
  await page.click('#add-drink');
  await page.click('#generate-bill');
  await expect(page.locator('#bill')).toHaveText('Bill for 2 items');

  await page.click('#pay-split');
  await page.click('#mark-paid');
  await expect(page.locator('#bill')).toHaveText('Paid');

  await page.click('#soft-delete-item');
  await page.click('#soft-delete-table');

  await page.route('**/add-pizza', (route) => route.fulfill({ status: 403 }));
  const itemStatus = await page.evaluate(() => fetch('http://localhost/add-pizza').then(r => r.status));
  expect(itemStatus).toBe(403);

  await page.route('**/place-order', (route) => route.fulfill({ status: 403 }));
  const tableStatus = await page.evaluate(() => fetch('http://localhost/place-order').then(r => r.status));
  expect(tableStatus).toBe(403);
});
