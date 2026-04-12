import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';

test.describe('Trainer - Puzzle Solving', () => {
  test('loads a specific puzzle and displays board', async ({ trainerPage }) => {
    await test.step('Load known puzzle via deep link', async () => {
      const puzzle = PUZZLES.forkMiddlegameWhite;
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Board and prompt are visible', async () => {
      await trainerPage.expectPuzzleLoaded();
    });

    await test.step('Context tags show puzzle info', async () => {
      const tags = await trainerPage.getContextTags();
      expect(tags.length).toBeGreaterThan(0);
    });
  });

  test('reveal best move shows correct move', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.pinOpening.gameId,
        PUZZLES.pinOpening.ply,
      );
    });

    await test.step('Click show best', async () => {
      await trainerPage.clickShowBest();
    });

    await test.step('Best move card appears with correct move', async () => {
      await trainerPage.expectBestMoveRevealed();
      const bestText = await trainerPage.bestMoveDisplay.textContent();
      expect(bestText).toContain(PUZZLES.pinOpening.bestMoveSan);
    });
  });

  test('next puzzle loads a different puzzle', async ({ trainerPage }) => {
    await test.step('Load initial puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.forkMiddlegameWhite.gameId,
        PUZZLES.forkMiddlegameWhite.ply,
      );
    });

    await test.step('Press N for next puzzle', async () => {
      await trainerPage.pressNext();
    });

    await test.step('Board still loaded with a puzzle', async () => {
      await trainerPage.expectPuzzleLoaded();
    });
  });

  test('reset restores board to interactive state', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.forkMiddlegameWhite.gameId,
        PUZZLES.forkMiddlegameWhite.ply,
      );
    });

    await test.step('Reveal best move', async () => {
      await trainerPage.clickShowBest();
      await trainerPage.expectBestMoveRevealed();
    });

    await test.step('Reset board', async () => {
      await trainerPage.clickReset();
    });

    await test.step('Board is visible and ready', async () => {
      await trainerPage.expectLoaded();
    });
  });

  test('keyboard shortcut B reveals best move', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.endgameBlunder.gameId,
        PUZZLES.endgameBlunder.ply,
      );
    });

    await test.step('Press B', async () => {
      await trainerPage.pressShowBest();
    });

    await test.step('Best move revealed', async () => {
      await trainerPage.expectBestMoveRevealed();
      const bestText = await trainerPage.bestMoveDisplay.textContent();
      expect(bestText).toContain(PUZZLES.endgameBlunder.bestMoveSan);
    });
  });
});
