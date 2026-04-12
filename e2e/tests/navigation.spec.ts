import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';
import { enableFeatureFlags, resetFeatureFlags } from '../helpers/api';

test.describe('Navigation', () => {
  test('trainer page loads at root', async ({ trainerPage }) => {
    await trainerPage.goto();
    await trainerPage.expectLoaded();
    await trainerPage.expectNavVisible();
  });

  test('dashboard page loads', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    await dashboardPage.expectLoaded();
  });

  test('settings page loads', async ({ settingsPage }) => {
    await settingsPage.goto();
    await settingsPage.expectLoaded();
  });

  test('management page loads', async ({ managementPage }) => {
    await managementPage.goto();
    await managementPage.expectLoaded();
  });

  test('nav links navigate between pages', async ({ trainerPage, page }) => {
    await test.step('Start at trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Navigate to dashboard via nav', async () => {
      await trainerPage.clickNavLink('Dashboard');
      await page.waitForURL('**/dashboard');
    });

    await test.step('Navigate to settings via nav', async () => {
      const settingsLink = page.locator('#mainNav').getByRole('link', { name: 'Settings' });
      await settingsLink.click();
      await page.waitForURL('**/settings');
    });

    await test.step('Navigate back to trainer', async () => {
      const trainerLink = page.locator('#mainNav').getByRole('link', { name: 'Trainer' });
      await trainerLink.click();
      await page.waitForURL(/\/$/);
    });
  });

  test('health endpoint responds', async ({ request }) => {
    const response = await request.get('/health');
    expect(response.ok()).toBeTruthy();
  });

  test('game review page loads', async ({ gameReviewPage, request }) => {
    await test.step('Enable game review feature', async () => {
      await enableFeatureFlags(request, { 'page.game_review': true });
    });

    await test.step('Navigate to game review', async () => {
      const puzzle = PUZZLES.forkMiddlegameWhite;
      await gameReviewPage.goto(puzzle.gameId);
    });

    await test.step('Page renders', async () => {
      await gameReviewPage.expectLoaded();
    });

    await test.step('Reset feature', async () => {
      await resetFeatureFlags(request, { 'page.game_review': false });
    });
  });
});
