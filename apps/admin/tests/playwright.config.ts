import { defineConfig } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const adminBaseURL = process.env.ADMIN_BASE_URL || baseURL;

export default defineConfig({
  testDir: '.',
  reporter: [['html', { open: 'never' }]],
  use: {
    headless: true,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    baseURL: adminBaseURL,
  },
});
