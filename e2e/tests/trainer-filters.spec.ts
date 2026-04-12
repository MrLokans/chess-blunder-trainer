import { test, expect } from '../fixtures/app.fixture';
import { enableFeatureFlags, resetFeatureFlags } from '../helpers/api';

test.describe('Trainer - Filters', () => {
  test('filters panel toggles open and closed', async ({ trainerPage }) => {
    await test.step('Load trainer — filters visible by default', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
      const content = trainerPage.page.locator('.filters-content').first();
      await expect(content).toBeVisible();
    });

    await test.step('Toggle filters closed', async () => {
      await trainerPage.toggleFiltersPanel();
      const content = trainerPage.page.locator('.game-type-filter');
      await expect(content).not.toBeVisible();
    });

    await test.step('Toggle filters open again', async () => {
      await trainerPage.toggleFiltersPanel();
      const content = trainerPage.page.locator('.game-type-filter');
      await expect(content).toBeVisible();
    });
  });

  test('color filter changes puzzle selection', async ({ trainerPage }) => {
    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Select white-only filter', async () => {
      const responsePromise = trainerPage.page.waitForResponse(
        resp => resp.url().includes('/api/puzzle') && resp.status() === 200,
      );
      await trainerPage.setColorFilter('white');
      await responsePromise;
    });

    await test.step('Puzzle loaded or empty state shown', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test('game type filter narrows results', async ({ trainerPage }) => {
    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Uncheck blitz game type', async () => {
      const responsePromise = trainerPage.page.waitForResponse(
        resp => resp.url().includes('/api/puzzle'),
      );
      await trainerPage.uncheckGameTypeFilter('blitz');
      await responsePromise;
    });

    await test.step('Puzzle loaded or empty state shown', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test('filter count badge updates', async ({ trainerPage }) => {
    await test.step('Load trainer', async () => {
      await trainerPage.goto();
      await trainerPage.expectLoaded();
    });

    await test.step('Apply color filter', async () => {
      const responsePromise = trainerPage.page.waitForResponse(
        resp => resp.url().includes('/api/puzzle'),
      );
      await trainerPage.setColorFilter('white');
      await responsePromise;
    });

    await test.step('Badge shows count', async () => {
      await trainerPage.expectActiveFilterCount(1);
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

    await test.step('Phase filter section visible', async () => {
      const phaseSection = trainerPage.page.locator('.phase-filter');
      await expect(phaseSection).toBeVisible();
    });

    await test.step('Click a phase filter and get response', async () => {
      const phaseSection = trainerPage.page.locator('.phase-filter');
      const endgameLabel = phaseSection.locator('label.filter-checkbox-label', { hasText: /endgame/i });
      const responsePromise = trainerPage.page.waitForResponse(
        resp => resp.url().includes('/api/puzzle'),
      );
      await endgameLabel.click();
      await responsePromise;
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

    await test.step('Tactical filter section visible', async () => {
      const tacticalSection = trainerPage.page.locator('.tactical-filter');
      await expect(tacticalSection).toBeVisible();
    });

    await test.step('Click a tactical pattern button', async () => {
      const btn = trainerPage.page.locator('.tactical-filter-btn').first();
      const responsePromise = trainerPage.page.waitForResponse(
        resp => resp.url().includes('/api/puzzle'),
      );
      await btn.click();
      await responsePromise;
    });

    await test.step('Puzzle loaded or empty state', async () => {
      await trainerPage.expectBoardOrEmptyState();
    });
  });

  test.afterAll(async ({ request }) => {
    await resetFeatureFlags(request, RESET_FLAGS);
  });
});
