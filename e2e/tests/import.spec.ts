import { test } from '../fixtures/app.fixture';

// Short game — fewer moves = faster Stockfish analysis
const TEST_PGN = `[Event "E2E Test"]
[Site "Test"]
[Date "2024.01.01"]
[White "TestWhite"]
[Black "TestBlack"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1500"]
[TimeControl "600"]

1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7# 1-0`;

test.describe('Import', () => {
  // Stockfish analysis is CPU-bound — short games still take a few seconds
  test('import valid PGN and see results', async ({ importPage }) => {
    test.setTimeout(120_000);
    await test.step('Load import page', async () => {
      await importPage.goto();
      await importPage.expectLoaded();
    });

    await test.step('Paste PGN', async () => {
      await importPage.pastePGN(TEST_PGN);
    });

    await test.step('Submit import', async () => {
      await importPage.submit();
    });

    await test.step('Wait for analysis to complete', async () => {
      await importPage.expectImportComplete();
    });
  });

  test('invalid PGN shows error', async ({ importPage }) => {
    await test.step('Load import page', async () => {
      await importPage.goto();
      await importPage.expectLoaded();
    });

    await test.step('Paste invalid PGN', async () => {
      await importPage.pastePGN('not a pgn at all');
    });

    await test.step('Submit', async () => {
      await importPage.submit();
    });

    await test.step('Error displayed', async () => {
      await importPage.expectErrors();
    });
  });
});
