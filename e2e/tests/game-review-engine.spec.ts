import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';
import { enableFeatureFlags, resetFeatureFlags } from '../helpers/api';

const FLAGS = { 'page.game_review': true, 'review.engine': true };

test.describe('Game review engine', () => {
  test.beforeEach(async ({ request }) => {
    await enableFeatureFlags(request, FLAGS);
  });

  test.afterEach(async ({ request }) => {
    await resetFeatureFlags(request, { 'page.game_review': false, 'review.engine': false });
  });

  test('analysis mode reveals the engine controls and lines panel', async ({ gameReviewPage, page }) => {
    await gameReviewPage.goto(PUZZLES.forkMiddlegameWhite.gameId);
    await gameReviewPage.expectLoaded();

    // Controls render whenever the review.engine flag is on (deterministic).
    await expect(page.locator('#engineControls')).toBeVisible();

    await gameReviewPage.enableAnalysis();

    // The multi-PV selector (a Segmented control, role="group") renders as soon as
    // analysis mode is on (no engine needed).
    await expect(page.locator('#engineControls').getByRole('group', { name: /lines/i })).toBeVisible();

    // End-to-end smoke: the (single-threaded) engine actually loads and produces
    // lines, so the panel becomes visible. Generous timeout for WASM load.
    await expect(page.locator('#engineLines')).toBeVisible({ timeout: 30_000 });
  });
});
