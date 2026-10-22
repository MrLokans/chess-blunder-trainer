import { test, expect } from '../fixtures/app.fixture';

test.describe('Dashboard', () => {
  test('displays stats cards with data from demo DB', async ({ dashboardPage }) => {
    await test.step('Load dashboard', async () => {
      await dashboardPage.goto();
      await dashboardPage.expectLoaded();
    });

    await test.step('KPI strip shows demo data', async () => {
      await expect(dashboardPage.kpis).toHaveCount(4);
      await expect(dashboardPage.kpis.first().locator('strong')).not.toHaveText('0');
    });
  });

  test('progressively discloses secondary insights', async ({ dashboardPage }) => {
    await dashboardPage.goto();
    await dashboardPage.expectLoaded();

    await expect(dashboardPage.moreInsights).not.toHaveAttribute('open', '');
    await dashboardPage.moreInsights.locator('summary').click();
    await expect(dashboardPage.moreInsights).toHaveAttribute('open', '');
    await expect(dashboardPage.management).toBeVisible();
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
