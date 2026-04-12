import { test, expect } from '../fixtures/app.fixture';

test.describe('Setup', () => {
  test('setup page redirects to trainer when already configured', async ({ page }) => {
    await page.goto('/setup');
    await page.waitForLoadState('networkidle');
    // Demo DB has setup_completed=true, so /setup redirects to /
    await expect(page).not.toHaveURL(/\/setup/);
  });

  test('trainer loads without setup redirect (demo DB has setup_completed)', async ({ trainerPage }) => {
    await test.step('Go to trainer root', async () => {
      await trainerPage.goto();
    });

    await test.step('Not redirected to setup', async () => {
      await expect(trainerPage.page).not.toHaveURL(/\/setup/);
      await trainerPage.expectLoaded();
    });
  });
});
