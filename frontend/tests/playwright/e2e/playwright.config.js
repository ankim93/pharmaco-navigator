// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * Pharmaco-Navigator Playwright E2E Configuration
 */

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  retries: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    // Capture screenshot + trace on first failure
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'simulated-launch',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3000',
        // Session cookies required by the backend BFF pattern
        contextOptions: { ignoreHTTPSErrors: true },
      },
    },
    {
      name: 'cerner-ehr-launch',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: 'http://localhost:3000',
        contextOptions: { ignoreHTTPSErrors: true },
        launchOptions: { slowMo: 300 },
      },
    },
  ],
});
