import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';

test.describe('Trainer - Vim Mode', () => {
  test('colon opens vim input', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.pinOpening.gameId,
        PUZZLES.pinOpening.ply,
      );
    });

    await test.step('Press colon', async () => {
      await trainerPage.openVimMode();
    });

    await test.step('Vim input is visible and focused', async () => {
      await expect(trainerPage.vimInput).toBeVisible();
      await expect(trainerPage.vimInputField).toBeFocused();
    });
  });

  test('escape closes vim input', async ({ trainerPage }) => {
    await test.step('Load puzzle and open vim', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.pinOpening.gameId,
        PUZZLES.pinOpening.ply,
      );
      await trainerPage.openVimMode();
    });

    await test.step('Press Escape', async () => {
      await trainerPage.closeVimMode();
    });

    await test.step('Vim input hidden', async () => {
      await expect(trainerPage.vimInput).not.toBeVisible();
    });
  });

  test('valid move via vim triggers submission', async ({ trainerPage }) => {
    const puzzle = PUZZLES.pinOpening;

    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(puzzle.gameId, puzzle.ply);
    });

    await test.step('Type best move in vim mode', async () => {
      await trainerPage.typeVimMoveAndWaitForSubmit(puzzle.bestMoveSan);
    });

    await test.step('Correct feedback shown', async () => {
      await trainerPage.expectCorrectFeedback();
    });
  });

  test('invalid notation shows error in vim', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.pinOpening.gameId,
        PUZZLES.pinOpening.ply,
      );
    });

    await test.step('Type nonsense in vim mode and submit', async () => {
      await trainerPage.openVimMode();
      await trainerPage.vimInputField.pressSequentially('Zz9');
      await trainerPage.vimInputField.press('Enter');
    });

    await test.step('Vim overlay shows error state', async () => {
      // Invalid notation keeps vim open with shake/error — overlay stays active
      await expect(trainerPage.vimInput).toHaveClass(/active/);
    });
  });

  test('vim suggestions appear while typing', async ({ trainerPage }) => {
    await test.step('Load puzzle', async () => {
      await trainerPage.loadSpecificPuzzle(
        PUZZLES.pinOpening.gameId,
        PUZZLES.pinOpening.ply,
      );
    });

    await test.step('Open vim and type partial move', async () => {
      await trainerPage.openVimMode();
      await trainerPage.vimInputField.fill('N');
    });

    await test.step('Suggestions dropdown visible', async () => {
      await expect(trainerPage.vimSuggestions).toBeVisible();
      const items = trainerPage.vimSuggestions.locator('.vim-suggestion');
      await expect(items.first()).toBeVisible();
    });
  });
});
