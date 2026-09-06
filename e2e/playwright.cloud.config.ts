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
const TMP_DIR = resolve(__dirname, '.tmp-cloud');
const AUTH_SECRET_KEY = 'x'.repeat(64);
const CLOUD_PORT = '8002';
const CLOUD_BASE_URL = `http://localhost:${CLOUD_PORT}`;
const FAKE_STOCKFISH = resolve(__dirname, 'fake-stockfish.sh');

// Billing E2E runs against the STUB Stripe gateway (STRIPE_STUB=true):
// no network calls to Stripe, but webhook SIGNATURE VERIFICATION stays
// real — the spec signs payloads with this secret via node:crypto.
// Subscription state is encoded in the subscription id the spec puts on
// each webhook event (see blunder_tutor/billing/stub_gateway.py).
export const STUB_WEBHOOK_SECRET = 'whsec_e2e_stub_secret';

export default defineConfig({
  testDir: './tests',
  testMatch: 'billing.spec.ts',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  globalSetup: resolve(__dirname, 'cloud.global-setup.ts'),
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report-cloud' }],
    ['list'],
  ],
  use: {
    baseURL: CLOUD_BASE_URL,
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
    // Same wipe-inside-the-spawning-shell pattern as the auth config:
    // cleanup must precede the app's aiosqlite handles.
    command: [
      `npm run build --prefix "${PROJECT_ROOT}"`,
      `rm -rf "${TMP_DIR}"`,
      `mkdir -p "${TMP_DIR}"`,
      `uv run python -m uvicorn blunder_tutor.web.app:create_app_factory --factory --host 0.0.0.0 --port ${CLOUD_PORT}`,
    ].join(' && '),
    cwd: PROJECT_ROOT,
    url: `${CLOUD_BASE_URL}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...forwardEnv(),
      DB_PATH: resolve(TMP_DIR, 'main.sqlite3'),
      AUTH_MODE: 'credentials',
      SECRET_KEY: AUTH_SECRET_KEY,
      MAX_USERS: '2',
      STOCKFISH_BINARY: FAKE_STOCKFISH,
      CLOUD_MODE: 'true',
      STRIPE_STUB: 'true',
      STRIPE_SECRET_KEY: 'sk_test_stub',
      STRIPE_WEBHOOK_SECRET: STUB_WEBHOOK_SECRET,
      STRIPE_PRICE_MONTHLY: 'price_m',
      STRIPE_PRICE_ANNUAL: 'price_a',
      PUBLIC_BASE_URL: CLOUD_BASE_URL,
    },
  },
});
