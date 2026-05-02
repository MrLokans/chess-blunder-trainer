import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page, type Route } from '@playwright/test';

const INVITE_FILE = resolve(__dirname, '..', '.tmp-setup-import', 'invite.txt');
const PASSWORD = 'password123';

interface ProfileShape {
  id: number;
  platform: 'lichess' | 'chesscom';
  username: string;
  is_primary: boolean;
  created_at: string;
  last_validated_at: string | null;
  preferences: { auto_sync_enabled: boolean; sync_max_games: number | null };
  stats: never[];
  last_game_sync_at: string | null;
  last_stats_sync_at: string | null;
}

function readInvite(): string {
  return readFileSync(INVITE_FILE, 'utf-8').trim();
}

function makeProfile(id: number, platform: 'lichess' | 'chesscom', username: string): ProfileShape {
  return {
    id,
    platform,
    username,
    is_primary: true,
    created_at: '2026-05-01T00:00:00Z',
    last_validated_at: null,
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [],
    last_game_sync_at: null,
    last_stats_sync_at: null,
  };
}

/**
 * Mocks every `/api/profiles*` endpoint that the SetupApp + BulkImportPanel
 * touch, so the test does not depend on Lichess/Chess.com network reachability
 * or timing. Intercepts run at the browser layer; the real backend is left
 * to handle session, `/api/setup/complete`, and `/api/auth/me` so the
 * authenticated routing through middleware still flows end-to-end.
 *
 * Returns a request-counters object the caller asserts against.
 */
function mockProfileEndpoints(page: Page) {
  const counters = { create: 0, sync: 0, validate: 0, list: 0 };
  const profiles: ProfileShape[] = [];

  void page.route('**/api/profiles/validate', async (route: Route) => {
    counters.validate += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        exists: true,
        already_tracked: false,
        profile_id: null,
        rate_limited: false,
      }),
    });
  });

  void page.route('**/api/profiles', async (route: Route) => {
    if (route.request().method() === 'POST') {
      counters.create += 1;
      const body = route.request().postDataJSON() as {
        platform: 'lichess' | 'chesscom';
        username: string;
      };
      const newProfile = makeProfile(profiles.length + 1, body.platform, body.username);
      profiles.push(newProfile);
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newProfile),
      });
      return;
    }
    // GET — used by BulkImportPanel after we navigate to /management.
    counters.list += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ profiles }),
    });
  });

  void page.route(/\/api\/profiles\/\d+\/sync$/, async (route: Route) => {
    counters.sync += 1;
    const url = route.request().url();
    const id = url.match(/\/api\/profiles\/(\d+)\/sync$/)?.[1] ?? '0';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: `mocked-job-${id}-${String(counters.sync)}` }),
    });
  });

  // `setup.waitForAnalysis` polls `/api/analysis/status`; resolve immediately
  // so the SetupApp's 15s poll loop short-circuits and the redirect to `/`
  // fires within seconds.
  void page.route('**/api/analysis/status', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'completed' }),
    });
  });

  return counters;
}

async function signupAsBob(page: Page): Promise<void> {
  const invite = readInvite();
  await page.goto('/setup');
  await page.fill('input[name="invite_code"]', invite);
  await page.fill('input[name="username"]', 'bob');
  await page.fill('input[name="password"]', PASSWORD);
  await Promise.all([
    page.waitForURL((url) => ['/', '/setup', '/trainer'].includes(url.pathname)),
    page.click('button[type="submit"]'),
  ]);
  await expect.poll(async () => (await page.request.get('/api/auth/me')).status())
    .toBe(200);
}

test.describe('Setup → Bulk Import (post-rewrite, profile-aware)', () => {
  test('signup → username form → profiles created → bulk import dispatches', async ({ page }) => {
    test.setTimeout(60_000);
    const counters = mockProfileEndpoints(page);

    // 1. First-user signup with the invite. After this `setup_completed`
    //    is still false, so `/setup` renders the SetupApp username form.
    await signupAsBob(page);

    // 2. /setup now renders the rewritten SetupApp. Fill both fields.
    await page.goto('/setup');
    await expect(page.locator('#setupForm')).toBeVisible();
    await page.locator('#lichess').fill('magnus_lichess');
    await page.locator('#chesscom').fill('magnus_chesscom');

    // Wait for the debounced validate calls to land before submit so the
    // form has a 'valid' state for both fields.
    await expect.poll(() => counters.validate, { timeout: 5_000 }).toBeGreaterThanOrEqual(2);

    // 3. Submit. SetupApp should: (a) re-validate, (b) POST /api/profiles
    //    twice, (c) POST /api/profiles/{id}/sync twice, (d) POST
    //    /api/setup/complete, (e) redirect to '/' once analysis.status
    //    returns 'completed'.
    const setupCompletePromise = page.waitForResponse((resp) =>
      resp.url().endsWith('/api/setup/complete') && resp.request().method() === 'POST',
    );
    await page.locator('#submitBtn').click();

    const completeResp = await setupCompletePromise;
    expect(completeResp.status()).toBe(200);

    // 4. Two profiles created, two syncs dispatched.
    expect(counters.create).toBe(2);
    expect(counters.sync).toBe(2);

    // 5. setup_completed is now true on the backend — the next /setup
    //    request should redirect away.
    await page.goto('/setup');
    await expect(page).not.toHaveURL(/\/setup$/);

    // 6. Navigate to /management. BulkImportPanel should render with both
    //    profiles, primary one selected by default, "Run import" visible.
    await page.goto('/management');
    await expect(page.locator('#bulk-import-profile')).toBeVisible({ timeout: 10_000 });
    const options = await page.locator('#bulk-import-profile option').allTextContents();
    expect(options).toHaveLength(2);
    expect(options.some((o) => o.includes('magnus_lichess'))).toBe(true);
    expect(options.some((o) => o.includes('magnus_chesscom'))).toBe(true);

    // 7. Click "Run import" → another sync dispatch.
    const syncCountBefore = counters.sync;
    await page.getByRole('button', { name: /Run import/i }).click();
    await expect.poll(() => counters.sync, { timeout: 5_000 }).toBe(syncCountBefore + 1);
  });
});
