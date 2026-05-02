import { resolve } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Mirrors `playwright.auth.config.ts`: credentials mode + fresh DB on
// each run, but on its own port and tmp dir so the two suites don't race
// over the single-use first-user invite. The setup→bulk-import flow
// needs to sign up from `user_count == 0` to exercise SetupApp; that
// only works against a fresh `auth.sqlite3` whose invite hasn't been
// consumed yet.
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
const TMP_DIR = resolve(__dirname, '.tmp-setup-import');
const AUTH_SECRET_KEY = 'y'.repeat(64);
const AUTH_PORT = '8002';
const AUTH_BASE_URL = `http://localhost:${AUTH_PORT}`;
const FAKE_STOCKFISH = resolve(__dirname, 'fake-stockfish.sh');

export default defineConfig({
  testDir: './tests',
  testMatch: 'setup-and-import.spec.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  globalSetup: resolve(__dirname, 'setup-import.global-setup.ts'),
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report-setup-import' }],
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
    command: [
      `npm run build --prefix "${PROJECT_ROOT}"`,
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
