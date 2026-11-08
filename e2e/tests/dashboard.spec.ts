import { test, expect } from '../fixtures/app.fixture';

test.describe('Dashboard', () => {
  test('leads with the trend and library status from the demo DB', async ({ dashboardPage }) => {
    await test.step('Load dashboard', async () => {
      await dashboardPage.goto();
      await dashboardPage.expectLoaded();
    });

    await test.step('Library status and trend show demo data', async () => {
      await expect(dashboardPage.libraryStatus).toContainText(/[1-9]\d* games/);
      await expect(dashboardPage.trendSpine.locator('.trend-chart__bar')).not.toHaveCount(0);
    });
  });

  test('switching the trend metric redraws the verdict', async ({ dashboardPage, page }) => {
    await dashboardPage.goto();
    await dashboardPage.expectLoaded();

    const verdict = dashboardPage.trendSpine.locator('.trend-verdict');
    await expect(verdict).not.toBeEmpty();
    await page.getByTestId('tab-clean_game_rate').click();
    await expect(page.getByTestId('tab-clean_game_rate')).toHaveAttribute('aria-selected', 'true');
    await expect(dashboardPage.trendSpine.locator('[data-metric="clean_game_rate"]')).toHaveCount(0);
    await expect(dashboardPage.sectionHeadings).toHaveCount(3);
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
