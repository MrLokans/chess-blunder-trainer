import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';

test.describe('Trainer - Click-based Moves', () => {
  test('click correct best move submits and shows feedback', async ({ trainerPage }) => {
    const puzzle = PUZZLES.endgameBlunder;

    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Click best move squares', async () => {
      await trainerPage.makeMoveAndWaitForSubmit(puzzle.bestMoveFrom, puzzle.bestMoveTo);
    });

    await test.step('Correct feedback shown', async () => {
      await trainerPage.expectCorrectFeedback();
    });
  });

  test('click wrong move and submit shows non-best feedback', async ({ trainerPage }) => {
    const puzzle = PUZZLES.forkMiddlegameWhite;
    // bestMove is Nf3+ (e5f3), replay the original blunder Qxg5+ (d8g5) instead
    const wrongFrom = 'd8';
    const wrongTo = 'g5';

    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Click wrong move and submit', async () => {
      await trainerPage.makeMove(wrongFrom, wrongTo);
      const responsePromise = trainerPage.page.waitForResponse('**/api/submit');
      await trainerPage.submitBtn.click();
      await responsePromise;
    });

    await test.step('Result card shows (not accent-correct)', async () => {
      await expect(trainerPage.resultCard).toBeVisible();
      await expect(trainerPage.resultCard).not.toHaveClass(/accent-correct/);
    });
  });

  test('click move on black-oriented board works', async ({ trainerPage }) => {
    const puzzle = PUZZLES.forkMiddlegameBlack;

    await test.step('Load black puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Click best move on flipped board', async () => {
      await trainerPage.makeMoveAndWaitForSubmit(puzzle.bestMoveFrom, puzzle.bestMoveTo);
    });

    await test.step('Correct feedback shown', async () => {
      await trainerPage.expectCorrectFeedback();
    });
  });

  test('click move then reset restores board', async ({ trainerPage }) => {
    const puzzle = PUZZLES.pinOpening;

    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Make best move', async () => {
      await trainerPage.makeMoveAndWaitForSubmit(puzzle.bestMoveFrom, puzzle.bestMoveTo);
    });

    await test.step('Reset board', async () => {
      await trainerPage.clickReset();
    });

    await test.step('Board is still loaded', async () => {
      await trainerPage.expectLoaded();
    });
  });

  test('click move then next puzzle loads new position', async ({ trainerPage }) => {
    const puzzle = PUZZLES.openingSimple;

    await test.step('Load puzzle and solve', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
      await trainerPage.makeMoveAndWaitForSubmit(puzzle.bestMoveFrom, puzzle.bestMoveTo);
    });

    await test.step('Load next puzzle', async () => {
      await trainerPage.clickNext();
    });

    await test.step('New puzzle loaded', async () => {
      await trainerPage.expectPuzzleLoaded();
    });
  });
});
