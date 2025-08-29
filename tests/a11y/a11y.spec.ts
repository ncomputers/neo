import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const guestBase = process.env.GUEST_BASE_URL || process.env.BASE_URL || '';
const kdsBase = process.env.KDS_BASE_URL || process.env.BASE_URL || '';
const adminBase = process.env.ADMIN_BASE_URL || process.env.BASE_URL || '';

test('guest menu has no serious accessibility violations', async ({ page }) => {
  await page.goto(`${guestBase}/menu`);
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(v => v.impact === 'serious' || v.impact === 'critical');
  expect(serious).toEqual([]);
});

test('kds expo has no serious accessibility violations', async ({ page }) => {
  await page.goto(`${kdsBase}/kds/expo`);
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(v => v.impact === 'serious' || v.impact === 'critical');
  expect(serious).toEqual([]);
});

test('admin dashboard has no serious accessibility violations', async ({ page }) => {
  await page.goto(`${adminBase}/dashboard`);
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(v => v.impact === 'serious' || v.impact === 'critical');
  expect(serious).toEqual([]);
});
