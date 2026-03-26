import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Pharmaco-Navigator E2E tests.
 */

export default defineConfig({
  // Location of all E2E test files
  testDir: './tests/e2e',

  // Give each test up to 30s before marking it as timed-out
  timeout: 30_000,

  // Retry once on CI to handle flaky network conditions
  retries: process.env.CI ? 1 : 0,

  // Run tests in parallel
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],

  // Shared settings
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },

  projects: [
    {
      // Standard headless project
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
      },
    },

    {
      // Presentation project
      name: 'presentation',
      use: {
        ...devices['Desktop Chrome'],
        headless: false,
        slowMo: 1000,
        viewport: { width: 1440, height: 900 },
        screenshot: 'on',
        video: 'on',
      },
    },
  ],

  // Dev-server lifecycle
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
