import { resolve } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Playwright's transform provides __dirname for config files
const PROJECT_ROOT = resolve(__dirname, '..');

export default defineConfig({
  testDir: './tests',
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
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'cp demo/demo.sqlite3 e2e/.tmp/test.sqlite3 && DB_PATH=e2e/.tmp/test.sqlite3 uv run python -m uvicorn blunder_tutor.web.app:create_app_factory --factory --host 0.0.0.0 --port 8000',
    cwd: PROJECT_ROOT,
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
