import { defineConfig } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const guestBaseURL = process.env.GUEST_BASE_URL || baseURL;
const kdsBaseURL = process.env.KDS_BASE_URL || baseURL;
const adminBaseURL = process.env.ADMIN_BASE_URL || baseURL;

export default defineConfig({
  testDir: './tests/e2e',
  reporter: [['html', { open: 'never' }]],
  use: {
    headless: true,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'guest', use: { baseURL: guestBaseURL } },
    { name: 'kds', use: { baseURL: kdsBaseURL } },
    { name: 'admin', use: { baseURL: adminBaseURL } },
  ],
});
