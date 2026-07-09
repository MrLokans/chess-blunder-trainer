import { DatabaseSync } from 'node:sqlite';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { test, expect } from '../fixtures/app.fixture';
import { PUZZLES } from '../fixtures/known-puzzles';
import { enableFeatureFlags, resetFeatureFlags } from '../helpers/api';

// Two topologies: locally the app runs on the host and its DB is directly
// writable via node:sqlite; in the Docker workflow the app (and the only
// consistent view of its WAL journal) lives inside a container, so SQL must
// run there via `docker exec` + the image's own Python.
const DB_PATH = resolve(__dirname, '../.tmp/test.sqlite3');
const DOCKER_CONTAINER = process.env.E2E_DOCKER_CONTAINER;
const DOCKER_DB_PATH = process.env.E2E_DOCKER_DB_PATH ?? '/app/data/main.sqlite3';

interface PuzzleDetail {
  fen: string;
  game_id: string;
  ply: number;
  blunder_uci: string;
  blunder_san: string;
  best_move_uci: string;
  best_move_san: string;
  best_line: string[];
  player_color: string;
  eval_after: number;
  best_move_eval: number | null;
}

interface SrsStatus {
  due: number;
  active: number;
  next_due_at: string | null;
}

function runSql(sql: string): void {
  if (DOCKER_CONTAINER) {
    const script = [
      'import sqlite3',
      `conn = sqlite3.connect(${JSON.stringify(DOCKER_DB_PATH)})`,
      `conn.execute(${JSON.stringify(sql)})`,
      'conn.commit()',
      'conn.close()',
    ].join('; ');
    execFileSync('docker', ['exec', DOCKER_CONTAINER, 'python3', '-c', script]);
    return;
  }
  const db = new DatabaseSync(DB_PATH);
  try {
    db.exec(sql);
  } finally {
    db.close();
  }
}

function wipeSrsCards(): void {
  runSql('DELETE FROM srs_cards');
}

test.describe('SRS Blunder Inbox', () => {
  test.beforeEach(async ({ request }) => {
    await enableFeatureFlags(request, { 'trainer.srs': true });
    wipeSrsCards();
  });

  test.afterEach(async ({ request }) => {
    await resetFeatureFlags(request, { 'trainer.srs': false });
    wipeSrsCards();
  });

  test('failed attempt enrolls; due review clears to inbox zero', async ({
    trainerPage, page, request,
  }) => {
    const puzzle = PUZZLES.forkMiddlegameWhite;

    await test.step('Fail the puzzle via API (replay the original blunder)', async () => {
      const detailResp = await request.get(
        `/api/puzzle/specific?game_id=${puzzle.gameId}&ply=${String(puzzle.ply)}`,
      );
      const detail = (await detailResp.json()) as PuzzleDetail;
      const submit = await request.post('/api/submit', {
        data: {
          move: detail.blunder_uci,
          fen: detail.fen,
          game_id: detail.game_id,
          ply: detail.ply,
          blunder_uci: detail.blunder_uci,
          blunder_san: detail.blunder_san,
          best_move_uci: detail.best_move_uci,
          best_move_san: detail.best_move_san,
          best_line: detail.best_line,
          player_color: detail.player_color,
          eval_after: detail.eval_after,
          best_move_eval: detail.best_move_eval,
        },
      });
      expect(submit.ok()).toBe(true);
    });

    await test.step('Card enrolled but due tomorrow — banner hidden', async () => {
      const status = (await (await request.get('/api/srs/status')).json()) as SrsStatus;
      expect(status.active).toBe(1);
      expect(status.due).toBe(0);
      await trainerPage.goto();
      await trainerPage.expectPuzzleLoaded();
      await expect(page.getByTestId('srs-review-banner')).toHaveCount(0);
    });

    await test.step('Force the card due now', async () => {
      runSql("UPDATE srs_cards SET due_at = '2000-01-01T00:00:00+00:00'");
      const status = (await (await request.get('/api/srs/status')).json()) as SrsStatus;
      expect(status.due).toBe(1);
    });

    await test.step('Banner appears; start review session', async () => {
      await trainerPage.goto();
      await expect(page.getByTestId('srs-review-banner')).toBeVisible();
      await expect(page.locator('#srsNavBadge')).toHaveText('1');
      const nextResponse = page.waitForResponse('**/api/srs/next');
      await page.getByTestId('srs-start-review').click();
      await nextResponse;
      await expect(page.getByTestId('srs-session-progress')).toHaveText('0 / 1');
    });

    await test.step('Solve the review, reach inbox zero', async () => {
      await trainerPage.makeMoveAndWaitForSubmit(puzzle.bestMoveFrom, puzzle.bestMoveTo);
      await expect(page.getByTestId('srs-session-progress')).toHaveText('1 / 1');
      await expect(page.locator('#srsNavBadge')).toBeHidden();
      await page.locator('#overlayNextBtn').click();
      await expect(page.getByTestId('srs-inbox-zero')).toBeVisible();
    });
  });
});
