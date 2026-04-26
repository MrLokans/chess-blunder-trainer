import { resolve } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Playwright's `webServer.env` REPLACES `process.env` rather than
// merging with it. `uv` needs its toolchain env (PATH) and cache
// resolution variables (HOME, UV_*, XDG_*, TMPDIR) to find Python
// on a fresh dev machine or in CI. Forward the minimal allowlist.
function forwardEnv(): Record<string, string> {
  const out: Record<string, string> = {};
  const alwaysForward = ['PATH', 'HOME', 'USER', 'TMPDIR', 'LANG', 'LC_ALL'];
  for (const key of alwaysForward) {
    const v = process.env[key];
    if (v !== undefined) out[key] = v;
  }
  for (const [key, value] of Object.entries(process.env)) {
    if (value === undefined) continue;
    if (key.startsWith('UV_') || key.startsWith('XDG_')) out[key] = value;
  }
  return out;
}

const PROJECT_ROOT = resolve(__dirname, '..');
const TMP_DIR = resolve(__dirname, '.tmp-auth');
const AUTH_SECRET_KEY = 'x'.repeat(64);
const AUTH_PORT = '8001';
const AUTH_BASE_URL = `http://localhost:${AUTH_PORT}`;
const FAKE_STOCKFISH = resolve(__dirname, 'fake-stockfish.sh');

// Separate config file instead of extending playwright.config.ts: the
// two test surfaces need *different* webServers (demo DB vs. fresh
// credentials DB) on *different* ports, and Playwright's webServer
// array is still a single startup barrier — overlapping them inside
// one config forces every run to boot both servers even when you're
// only running one suite.
export default defineConfig({
  testDir: './tests',
  testMatch: 'auth.spec.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  globalSetup: resolve(__dirname, 'auth.global-setup.ts'),
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report-auth' }],
    ['list'],
  ],
  use: {
    baseURL: AUTH_BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    // Wipe and recreate `.tmp-auth/` in the same shell that spawns
    // uvicorn so the cleanup happens *before* the app opens
    // `auth.sqlite3`. Doing it from globalSetup instead would race
    // the app's file handle — it runs AFTER webServer boot.
    command: [
      // Rebuild the Vite manifest so `src/auth/*.tsx` entries exist
      // before the app serves `/setup`. ~200ms when already fresh.
      `npm run build --prefix "${PROJECT_ROOT}"`,
      // Wipe then recreate the per-run tmp dir *inside* the same
      // shell that launches uvicorn, so the cleanup precedes any
      // aiosqlite handle on `auth.sqlite3`.
      `rm -rf "${TMP_DIR}"`,
      `mkdir -p "${TMP_DIR}"`,
      `uv run python -m uvicorn blunder_tutor.web.app:create_app_factory --factory --host 0.0.0.0 --port ${AUTH_PORT}`,
    ].join(' && '),
    cwd: PROJECT_ROOT,
    url: `${AUTH_BASE_URL}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...forwardEnv(),
      DB_PATH: resolve(TMP_DIR, 'main.sqlite3'),
      AUTH_MODE: 'credentials',
      SECRET_KEY: AUTH_SECRET_KEY,
      MAX_USERS: '2',
      STOCKFISH_BINARY: FAKE_STOCKFISH,
    },
  },
});
