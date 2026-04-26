import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const INVITE_FILE = resolve(__dirname, '..', '.tmp-auth', 'invite.txt');
const PASSWORD = 'password123';

interface MeResponse {
  id: string;
  username: string;
  email: string | null;
}

function readInvite(): string {
  return readFileSync(INVITE_FILE, 'utf-8').trim();
}

test.describe('Credentials auth flow', () => {
  test('signup → logout → login → delete account', async ({ page, context }) => {
    const invite = readInvite();

    // 1. First-user signup via the Preact form on /setup.
    //    Fresh `auth.sqlite3` means `user_count == 0`, so the /setup
    //    dispatcher renders `first_setup.html` with the invite-gated
    //    signup form (not the Lichess/chess.com username form).
    await page.goto('/setup');
    await page.fill('input[name="invite_code"]', invite);
    await page.fill('input[name="username"]', 'alice');
    await page.fill('input[name="password"]', PASSWORD);
    await Promise.all([
      // `/api/auth/me` is the real authentication signal; this URL
      // gate is just a "wait for nav to settle" barrier so the
      // subsequent request uses the cookie the form handler set.
      page.waitForURL((url) => ['/', '/setup', '/trainer'].includes(url.pathname)),
      page.click('button[type="submit"]'),
    ]);
    await expect.poll(async () => (await page.request.get('/api/auth/me')).status())
      .toBe(200);
    const me1 = (await (await page.request.get('/api/auth/me')).json()) as MeResponse;
    expect(me1).toMatchObject({ username: 'alice' });

    // 2. Logout via the JSON API (idempotent, returns 204).
    const logout = await page.request.post('/api/auth/logout');
    expect(logout.status()).toBe(204);
    await context.clearCookies();

    // 3. Login via the form.
    await page.goto('/login');
    await page.fill('input[name="username"]', 'alice');
    await page.fill('input[name="password"]', PASSWORD);
    await Promise.all([
      page.waitForURL((url) => ['/', '/setup', '/trainer'].includes(url.pathname)),
      page.click('button[type="submit"]'),
    ]);
    const me2 = (await (await page.request.get('/api/auth/me')).json()) as MeResponse;
    expect(me2).toMatchObject({ username: 'alice', id: me1.id });

    // 4. Delete the account; subsequent `/me` must 401.
    const del = await page.request.delete('/api/auth/account');
    expect(del.status()).toBe(204);
    const meAfter = await page.request.get('/api/auth/me');
    expect(meAfter.status()).toBe(401);

    // 5. Anonymous navigation to `/` redirects to `/login` in
    //    credentials mode.
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });
});
