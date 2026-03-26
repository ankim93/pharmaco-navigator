/**
 * E2E tests — Pharmaco-Navigator Dashboard
 */

import { test, expect } from '@playwright/test';

// Helpers

/**
 * Navigate to the dashboard for a given patient ID and wait for the loading spinner to disappear
 */
async function openDashboard(page, patientId = 'DEMO001') {
  await page.goto(`/?patient=${patientId}`);
  // Wait for spinner to be gone — either data grid or error will appear
  await page.waitForSelector('[data-testid="loading-spinner"]', {
    state: 'detached',
    timeout: 15_000,
  }).catch(() => {
    // Spinner may already be gone; continue
  });
}

// Suite
test.describe('Pharmaco-Navigator — Dashboard E2E', () => {

  test('page loads and displays the application title', async ({ page }) => {
    await page.goto('/');
    // Title in browser tab
    await expect(page).toHaveTitle(/Pharmaco-Navigator/i);
  });

  test('shows SMART launch error when no patient param is given', async ({ page }) => {
    await page.goto('/');
    await expect(
      page.getByText('SMART Launch Context Error')
    ).toBeVisible();
    await page.screenshot({ path: 'playwright-screenshots/01-smart-error.png', fullPage: true });
  });

  test('shows loading spinner while data is fetching', async ({ page }) => {
    // Intercept the alerts API and slow the response so the spinner is visible
    await page.route('**/api/v1/patient/*/alerts**', async (route) => {
      await page.waitForTimeout(1500);
      await route.continue();
    });
    await page.goto('/?patient=DEMO001');
    // The spinner should be present at some point during the delayed load
    await expect(
      page.getByText(/Loading clinical decision support data/i)
    ).toBeVisible({ timeout: 3000 });
    await page.screenshot({ path: 'playwright-screenshots/02-loading.png', fullPage: true });
  });

  test.describe('with DEMO001 (all risk levels)', () => {

    test.beforeEach(async ({ page }) => {
      await page.goto('/?patient=DEMO001');
      // Wait for header to appear
      await expect(page.getByText('Pharmaco-Navigator')).toBeVisible({ timeout: 15_000 });
    });

    test('renders the DashboardHeader with the patient ID', async ({ page }) => {
      await expect(page.getByText('DEMO001')).toBeVisible();
      await page.screenshot({ path: 'playwright-screenshots/03-dashboard-header.png', fullPage: true });
    });

    test('displays all three traffic-light columns', async ({ page }) => {
      await expect(page.getByText('High Risk')).toBeVisible();
      await expect(page.getByText('Moderate Risk')).toBeVisible();
      await expect(page.getByText('Safe / Standard Dosing')).toBeVisible();
      await page.screenshot({ path: 'playwright-screenshots/04-three-columns.png', fullPage: true });
    });

    test('shows the active medications panel', async ({ page }) => {
      await expect(page.getByText(/Active Medications/i)).toBeVisible();
    });

    test('displays a gene pill in the header for CYP2D6', async ({ page }) => {
      await expect(page.getByText('CYP2D6')).toBeVisible();
    });

    test('expands an alert card to reveal CPIC details', async ({ page }) => {
      // Click the first visible alert card chevron / expand button
      const firstCard = page.locator('[data-testid="alert-card"]').first();
      await firstCard.click();
      // After expand the clinical action text should be visible
      await expect(
        page.getByText(/avoid|use with caution|standard dosing|no cpic/i).first()
      ).toBeVisible();
      await page.screenshot({ path: 'playwright-screenshots/05-expanded-card.png', fullPage: true });
    });

    test('CPIC guideline link is present in expanded card', async ({ page }) => {
      const firstCard = page.locator('[data-testid="alert-card"]').first();
      await firstCard.click();
      const cpicLink = page.getByRole('link', { name: /CPIC.*Guideline/i }).first();
      await expect(cpicLink).toBeVisible();
      await expect(cpicLink).toHaveAttribute('href', /cpicpgx\.org/);
      await page.screenshot({ path: 'playwright-screenshots/06-cpic-link.png', fullPage: true });
    });

    test('footer shows CPIC guidelines attribution text', async ({ page }) => {
      await expect(
        page.getByText(/Clinical Pharmacogenomics Implementation Consortium/i)
      ).toBeVisible();
    });
  });

  test.describe('with DEMO002 (safe patient)', () => {

    test.beforeEach(async ({ page }) => {
      await page.goto('/?patient=DEMO002');
      await expect(page.getByText('Pharmaco-Navigator')).toBeVisible({ timeout: 15_000 });
    });

    test('shows no-high-risk empty-state message', async ({ page }) => {
      await expect(
        page.getByText('No high-risk drug interactions detected')
      ).toBeVisible();
      await page.screenshot({ path: 'playwright-screenshots/07-safe-patient.png', fullPage: true });
    });

    test('does not render the Data Missing/Unknown column', async ({ page }) => {
      await expect(page.getByText('Data Missing/Unknown')).not.toBeVisible();
    });
  });

  test.describe('error handling', () => {

    test('shows Backend Connection Error when API is unreachable', async ({ page }) => {
      // Abort all alert API requests to simulate a down backend
      await page.route('**/api/v1/patient/*/alerts**', route => route.abort());
      await page.goto('/?patient=DEMO001');
      await expect(page.getByText(/Backend Connection Error/i)).toBeVisible({ timeout: 10_000 });
      await page.screenshot({ path: 'playwright-screenshots/08-error-state.png', fullPage: true });
    });

    test('Retry Connection button is visible on error', async ({ page }) => {
      await page.route('**/api/v1/patient/*/alerts**', route => route.abort());
      await page.goto('/?patient=DEMO001');
      await expect(
        page.getByRole('button', { name: /Retry Connection/i })
      ).toBeVisible({ timeout: 10_000 });
    });
  });
});
