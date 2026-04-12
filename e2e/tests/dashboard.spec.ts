import { test, expect } from '../fixtures/app.fixture';

test.describe('Dashboard', () => {
  test('displays stats cards with data from demo DB', async ({ dashboardPage }) => {
    await test.step('Load dashboard', async () => {
      await dashboardPage.goto();
      await dashboardPage.expectLoaded();
    });

    await test.step('Stats cards are rendered', async () => {
      await expect(dashboardPage.statCards.nth(2)).toBeVisible();
    });
  });

  test('dashboard loads without console errors', async ({ dashboardPage, page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await dashboardPage.goto();
    await dashboardPage.expectLoaded();

    // Filter known non-critical errors
    const critical = errors.filter(e => !e.includes('favicon'));
    expect(critical).toHaveLength(0);
  });
});
