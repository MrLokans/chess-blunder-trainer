import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const INVITE_FILE = resolve(__dirname, '..', '.tmp-auth', 'invite.txt');
const PASSWORD = 'password123';
const USERNAME = 'alice';

interface MeResponse {
  id: string;
  username: string;
  email: string | null;
}

function readInvite(): string {
  return readFileSync(INVITE_FILE, 'utf-8').trim();
}

async function me(page: Page): Promise<MeResponse> {
  return (await (await page.request.get('/api/auth/me')).json()) as MeResponse;
}

// `/api/auth/me` is the real authentication signal; the URL gate is just
// a "wait for nav to settle" barrier so the request that follows uses
// the cookie the form handler set.
async function submitAuthForm(page: Page): Promise<void> {
  await Promise.all([
    page.waitForURL((url) => ['/', '/setup', '/trainer'].includes(url.pathname)),
    page.click('button[type="submit"]'),
  ]);
}

async function signup(page: Page, invite: string): Promise<void> {
  await page.goto('/setup');
  await page.fill('input[name="invite_code"]', invite);
  await page.fill('input[name="username"]', USERNAME);
  await page.fill('input[name="password"]', PASSWORD);
  await submitAuthForm(page);
}

test.describe('Credentials auth flow', () => {
  // Serial: the steps are inherently ordered and destructive (step 4
  // deletes the account), so a failure should skip the rest rather than
  // cascade into four unrelated-looking failures.
  test.describe.configure({ mode: 'serial' });

  // One browser context for the whole flow. The per-test `page` fixture
  // would hand each test a fresh context, dropping the session cookie
  // that steps 2-4 depend on.
  let page: Page;
  let userId: string;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('1. first-user signup authenticates the session', async () => {
    // Fresh `auth.sqlite3` means `user_count == 0`, so the /setup
    // dispatcher renders `first_setup.html` with the invite-gated
    // signup form (not the Lichess/chess.com username form).
    await signup(page, readInvite());

    await expect
      .poll(async () => (await page.request.get('/api/auth/me')).status())
      .toBe(200);
    const body = await me(page);
    expect(body).toMatchObject({ username: USERNAME });
    userId = body.id;
  });

  test('2. logout revokes the session server-side', async () => {
    const logout = await page.request.post('/api/auth/logout');
    expect(logout.status()).toBe(204);

    // Assert before clearing cookies: the session must be dead on the
    // server, not merely forgotten by the client.
    const meAfter = await page.request.get('/api/auth/me');
    expect(meAfter.status()).toBe(401);

    await page.context().clearCookies();
  });

  test('3. login restores the same user', async () => {
    await page.goto('/login');
    await page.fill('input[name="username"]', USERNAME);
    await page.fill('input[name="password"]', PASSWORD);
    await submitAuthForm(page);

    expect(await me(page)).toMatchObject({ username: USERNAME, id: userId });
  });

  test('4. delete account revokes the session', async () => {
    const del = await page.request.delete('/api/auth/account');
    expect(del.status()).toBe(204);

    const meAfter = await page.request.get('/api/auth/me');
    expect(meAfter.status()).toBe(401);
  });

  test('5. anonymous navigation redirects to login', async () => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });
});
