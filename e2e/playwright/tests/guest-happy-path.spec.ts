import { test, expect } from '@playwright/test';

test('guest can view menu, add items, place order and see bill', async ({ page }) => {
  await page.setContent(`
    <h1>Menu</h1>
    <button id="add-pizza">Add Pizza - $10</button>
    <div id="cart"></div>
    <button id="place-order">Place Order</button>
    <div id="bill"></div>
    <script>
      let total = 0;
      document.getElementById('add-pizza').addEventListener('click', () => {
        total += 10;
        document.getElementById('cart').textContent = 'Total: $' + total;
      });
      document.getElementById('place-order').addEventListener('click', () => {
        document.getElementById('bill').textContent = 'Bill: $' + total;
      });
    </script>
  `);

  await page.click('#add-pizza');
  await expect(page.locator('#cart')).toHaveText('Total: $10');

  await page.click('#place-order');
  await expect(page.locator('#bill')).toHaveText('Bill: $10');
});
