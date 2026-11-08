import { test, expect } from '../fixtures/app.fixture';

test.describe('Settings', () => {
  test('settings page renders', async ({ settingsPage }) => {
    await settingsPage.goto();
    await settingsPage.expectLoaded();
  });

  test('board display toggles on Settings apply to the trainer board', async ({ settingsPage, trainerPage, page }) => {
    await test.step('Turn coordinates off on Settings', async () => {
      await settingsPage.goto();
      await settingsPage.expectLoaded();
      const coordinates = page.locator('#boardDisplay-showCoordinates');
      await expect(coordinates).toBeChecked();
      await coordinates.uncheck();
    });

    await test.step('Trainer board hides coordinates', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
      await expect(page.locator('#board')).toHaveClass(/hide-coords/);
    });
  });

  test('locale change updates page language', async ({ settingsPage, page }) => {
    await test.step('Load settings', async () => {
      await settingsPage.goto();
      await settingsPage.expectLoaded();
    });

    await test.step('Change locale to Russian', async () => {
      const responsePromise = page.waitForResponse('**/api/settings/locale');
      await settingsPage.changeLocale('ru');
      await responsePromise;
    });

    await test.step('Page reloads with Russian text', async () => {
      await page.waitForLoadState('load');
      const navText = page.locator('#mainNav');
      await expect(navText).toContainText(/[\u0400-\u04FF]/);
    });

    // Always reset locale — even if assertions above fail, afterEach handles cleanup
  });

  test.afterEach(async ({ page }) => {
    // Ensure locale is always reset to English after any settings test
    try {
      await page.goto('/settings');
      await page.waitForLoadState('load');
      const select = page.getByRole('combobox').first();
      const currentValue = await select.inputValue();
      if (currentValue !== 'en') {
        const responsePromise = page.waitForResponse('**/api/settings/locale');
        await select.selectOption('en');
        await responsePromise;
      }
    } catch {
      // Best-effort cleanup
    }
  });
});
