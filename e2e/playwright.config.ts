import { resolve } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Playwright's transform provides __dirname for config files
const PROJECT_ROOT = resolve(__dirname, '..');

// Suites that need a credentials-mode webServer (fresh DB, fake stockfish) run
// via dedicated config files; excluded so `npx playwright test` doesn't spawn
// them against the demo DB, where signup endpoints don't apply.
const SEPARATE_CONFIG_SPECS = ['auth.spec.ts', 'setup-and-import.spec.ts'];

// These flip server-global feature flags or the UI locale, or write the DB
// directly, which changes what every other spec sees (e.g. `trainer.srs`
// reroutes the trainer, locale `ru` renames every button). They run one at a
// time, after the parallel suite.
const GLOBAL_STATE_SPECS = [
  'srs.spec.ts',
  'navigation.spec.ts',
  'trainer-filters.spec.ts',
  'game-review-engine.spec.ts',
  'settings.spec.ts',
];

export default defineConfig({
  testDir: './tests',
  testIgnore: SEPARATE_CONFIG_SPECS,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: [...SEPARATE_CONFIG_SPECS, ...GLOBAL_STATE_SPECS],
    },
    {
      name: 'chromium-global-state',
      use: { ...devices['Desktop Chrome'] },
      testMatch: GLOBAL_STATE_SPECS,
      dependencies: ['chromium'],
      workers: 1,
    },
  ],
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'cp demo/demo.sqlite3 e2e/.tmp/test.sqlite3 && DB_PATH=e2e/.tmp/test.sqlite3 uv run python -m uvicorn blunder_tutor.web.app:create_app_factory --factory --host 0.0.0.0 --port 8000',
    cwd: PROJECT_ROOT,
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
