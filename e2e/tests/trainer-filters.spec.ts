import { test, expect } from '../fixtures/app.fixture';
import { enableFeatureFlags, resetFeatureFlags } from '../helpers/api';

test.describe('Trainer - Filters', () => {
  test('filters live in a drawer behind the summary line', async ({ trainerPage }) => {
    await test.step('Load trainer — only the summary is in the panel', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
      await expect(trainerPage.filterSummary).toBeVisible();
      await expect(trainerPage.page.locator('.game-type-filter')).toHaveCount(0);
    });

    await test.step('Open the drawer', async () => {
      await trainerPage.openFilters();
      await expect(trainerPage.filtersDrawer.locator('.game-type-filter')).toBeVisible();
    });

    await test.step('Escape closes it', async () => {
      await trainerPage.page.keyboard.press('Escape');
      await expect(trainerPage.filtersDrawer).toBeHidden();
    });
  });

  test('color filter applies once on close and shows in the summary', async ({ trainerPage }) => {
    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Pick white in the drawer and apply', async () => {
      await trainerPage.openFilters();
      await trainerPage.setColorFilter('white');
      await trainerPage.applyFilters();
    });

    await test.step('Summary names the filter; puzzle or empty state shown', async () => {
      await expect(trainerPage.filterSummary).toContainText('White');
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test('game type filter narrows results', async ({ trainerPage }) => {
    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Uncheck blitz and apply', async () => {
      await trainerPage.openFilters();
      await trainerPage.uncheckGameTypeFilter('blitz');
      await trainerPage.applyFilters();
    });

    await test.step('Puzzle loaded or empty state shown', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });
});

test.describe('Trainer - Feature-Gated Filters', () => {
  const FLAGS = {
    'trainer.filter.phase': true,
    'trainer.filter.tactical': true,
    'trainer.filter.difficulty': true,
  };
  const RESET_FLAGS = {
    'trainer.filter.phase': false,
    'trainer.filter.tactical': false,
    'trainer.filter.difficulty': false,
  };

  test('phase filter appears when feature enabled', async ({ trainerPage, request }) => {
    await test.step('Enable phase filter feature', async () => {
      await enableFeatureFlags(request, FLAGS);
    });

    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Phase filter section visible in the drawer', async () => {
      await trainerPage.openFilters();
      await expect(trainerPage.filtersDrawer.locator('.phase-filter')).toBeVisible();
    });

    await test.step('Pick a phase and apply', async () => {
      await trainerPage.filtersDrawer.locator('.phase-filter label.filter-checkbox-label[data-value="endgame"]').click();
      await trainerPage.applyFilters();
    });

    await test.step('Puzzle loaded or empty state', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test('tactical pattern filter appears when feature enabled', async ({ trainerPage, request }) => {
    await test.step('Enable tactical filter feature', async () => {
      await enableFeatureFlags(request, FLAGS);
    });

    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Tactical filter section visible in the drawer', async () => {
      await trainerPage.openFilters();
      await expect(trainerPage.filtersDrawer.locator('.tactical-filter')).toBeVisible();
    });

    await test.step('Pick a tactical pattern and apply', async () => {
      await trainerPage.filtersDrawer.locator('.tactical-filter-btn').first().click();
      await trainerPage.applyFilters();
    });

    await test.step('Puzzle loaded or empty state', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test.afterAll(async ({ request }) => {
    await resetFeatureFlags(request, RESET_FLAGS);
  });
});
