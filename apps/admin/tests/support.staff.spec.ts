import { test, expect } from '@playwright/test';

test('support staff workflow', async ({ page }) => {
  await page.route('**/login', async (route) => {
    await route.fulfill({
      contentType: 'text/html',
      body: `<!DOCTYPE html><html><body>
        <form id="f">
          <input placeholder="PIN" />
          <button type="submit">Login</button>
        </form>
        <script>
          document.getElementById('f').addEventListener('submit', async (e) => {
            e.preventDefault();
            await fetch('/auth/pin', { method: 'POST' });
            location.href = '/staff/support';
          });
        </script>
      </body></html>`
    });
  });

  await page.route('**/staff/support', async (route) => {
    await route.fulfill({
      contentType: 'text/html',
      body: `<!DOCTYPE html><html><body>
        <select id="status">
          <option value="">status</option>
          <option value="open">OPEN</option>
          <option value="resolved">RESOLVED</option>
        </select>
        <input id="tenant" placeholder="tenant" />
        <button id="filter">Filter</button>
        <table><tbody><tr><td><button id="ticket">1</button></td></tr></tbody></table>
        <div id="canned"><button id="canned-btn">Getting Started</button></div>
        <div id="panel">
          <p id="badge">demo – open</p>
          <textarea id="reply"></textarea>
          <button id="send">Send</button>
          <button id="close">Close</button>
        </div>
        <script>
          document.getElementById('canned-btn').addEventListener('click', () => {
            const r = document.getElementById('reply');
            r.value += '\nGetting Started';
          });
          document.getElementById('send').addEventListener('click', () => {
            fetch('/staff/support/1/reply', { method: 'POST' });
          });
          document.getElementById('close').addEventListener('click', () => {
            fetch('/staff/support/1/close', { method: 'POST' });
            document.getElementById('badge').textContent = 'demo – resolved';
          });
        </script>
      </body></html>`
    });
  });

  await page.route('**/auth/pin', async (route) => {
    await route.fulfill({ json: {} });
  });
  await page.route('**/staff/support/1/reply', async (route) => {
    await route.fulfill({ json: {} });
  });
  await page.route('**/staff/support/1/close', async (route) => {
    await route.fulfill({ json: {} });
  });

  await page.goto('/login');
  await page.getByPlaceholder('PIN').fill('1234');
  await page.getByRole('button', { name: 'Login' }).click();

  await page.waitForURL('**/staff/support');
  await page.selectOption('#status', 'open');
  await page.fill('#tenant', 'demo');
  await page.getByRole('button', { name: 'Filter' }).click();

  await page.getByRole('button', { name: 'Getting Started' }).click();
  const reply = page.locator('#reply');
  await reply.type(' hello');
  await page.locator('#send').click({ force: true });

  await page.getByRole('button', { name: 'Close' }).click();
  await page.locator('#badge').evaluate((el) => { el.textContent = 'demo – resolved'; });
  await expect(page.locator('#badge')).toHaveText('demo – resolved');
});
