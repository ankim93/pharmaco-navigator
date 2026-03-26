// @ts-check
/**
 * Pharmaco-Navigator End-to-End Tests
 */

import { test, expect } from '@playwright/test';

// Shared helpers
async function waitForDashboard(page) {
  await page.waitForSelector('h2:has-text("High Risk")', { timeout: 30_000 });
}

async function clickFirstCard(page) {
  const firstCard = page.locator('[class*="border-2"][class*="rounded-lg"]').first();
  await expect(firstCard).toBeVisible({ timeout: 10_000 });

  // Capture the drug name shown in the card header
  const drugName = await firstCard.locator('h3').innerText();
  console.log(`[E2E] Clicking alert card: "${drugName}"`);

  const expandButton = firstCard.getByRole('button', { name: /View CPIC Guideline/i });
  await expandButton.click();

  const guidelineLink = firstCard.locator('a[href*="cpicpgx.org"]');
  await expect(guidelineLink).toBeVisible({ timeout: 5_000 });

  return drugName;
}


// Simulated SMART launch (no Cerner login required)
test.describe('Simulated SMART Launch', () => {
  test.use({ baseURL: 'http://localhost:3000' });

  test('loads dashboard for demo patient DEMO001', async ({ page }) => {
    // Direct URL with patient param simulates the SMART EHR launch context
    await page.goto('/?patient=DEMO001');
    await waitForDashboard(page);

    await expect(page.locator('text=CYP2D6').first()).toBeVisible();
  });

  test('shows at least one alert card for DEMO001', async ({ page }) => {
    await page.goto('/?patient=DEMO001');
    await waitForDashboard(page);

    // At least one alert card (any color) must be present
    const anyCards = page.locator('[class*="border-2"][class*="rounded-lg"]');
    await expect(anyCards.first()).toBeVisible({ timeout: 10_000 });
    const count = await anyCards.count();
    expect(count).toBeGreaterThan(0);
    console.log(`[E2E] Found ${count} alert card(s)`);
  });

  test('expands an alert card and shows CPIC guideline link', async ({ page }) => {
    await page.goto('/?patient=DEMO001');
    await waitForDashboard(page);

    const drugName = await clickFirstCard(page);
    expect(drugName.length).toBeGreaterThan(0);
  });

  test('active medications list is shown in the header', async ({ page }) => {
    await page.goto('/?patient=DEMO001');
    await waitForDashboard(page);

    // The active medication count is displayed in the info banner
    await expect(page.locator('text=/analyzes \\d+ medication/')).toBeVisible();
  });

  test('alert columns titles are all present', async ({ page }) => {
    await page.goto('/?patient=DEMO001');
    await waitForDashboard(page);

    for (const title of ['High Risk', 'Moderate Risk', 'Safe / Standard Dosing']) {
      await expect(page.locator(`h2:has-text("${title}")`)).toBeVisible();
    }
  });
});


// Full Cerner EHR launch (requires provider sandbox credentials)
test.describe('Cerner EHR Launch', () => {
  test.skip(
    !process.env.CERNER_SANDBOX_USER,
    'Skipped: set CERNER_SANDBOX_USER and CERNER_SANDBOX_PASSWORD to run Cerner EHR launch tests',
  );

  const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
  const ISS = 'https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d';

  test('full OAuth flow: Cerner login → dashboard → click red alert', async ({ page }) => {

    const launchToken = process.env.CERNER_LAUNCH_TOKEN || 'standalone';
    const launchURL =
      `${BACKEND_URL}/api/v1/auth/launch` +
      `?iss=${encodeURIComponent(ISS)}` +
      `&launch=${encodeURIComponent(launchToken)}`;

    await page.goto(launchURL);

   
    // Cerner redirects to their authorization / login page.
    await page.waitForURL(/authorization\.cerner\.com/, { timeout: 15_000 });

    const usernameField = page.locator('#username, [name="username"]');
    const passwordField = page.locator('#password, [name="password"], [type="password"]');
    const signInButton  = page.locator('#submitButton, [type="submit"]');

    await expect(usernameField).toBeVisible({ timeout: 10_000 });
    await usernameField.fill(process.env.CERNER_SANDBOX_USER);
    await passwordField.fill(process.env.CERNER_SANDBOX_PASSWORD);
    await signInButton.click();


    // Cerner presents an authorization consent screen.
    try {
      const allowButton = page.locator('button:has-text("Allow"), input[value="Allow"]');
      await allowButton.waitFor({ timeout: 5_000 });
      await allowButton.click();
    } catch {
      // No consent screen — continue
    }

  
    // Cerner redirects to backend /callback, which exchanges the
    // authorization code for an access token, stores it in the session, and
    // then redirects the browser to the frontend with the patient context.
    await page.waitForURL(/localhost:5173/, { timeout: 20_000 });


    // Wait for the Pharmaco-Navigator dashboard to load.
    await waitForDashboard(page);
    await expect(page.locator('text=/Patient ID/i')).toBeVisible();


    // Click an alert card and verify the guideline link expands.
    const drugName = await clickFirstCard(page);
    console.log(`[E2E] Successfully clicked alert: "${drugName}"`);

    await page.screenshot({
      path: `tests/e2e/screenshots/cerner-alert-${Date.now()}.png`,
      fullPage: false,
    });
  });
});
