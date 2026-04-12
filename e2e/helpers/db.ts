import { mkdirSync, copyFileSync, existsSync, unlinkSync } from 'node:fs';
import { resolve } from 'node:path';

// Playwright's transform provides __dirname
const DEMO_DB = resolve(__dirname, '../../demo/demo.sqlite3');
const TMP_DIR = resolve(__dirname, '../.tmp');
const TEST_DB = resolve(TMP_DIR, 'test.sqlite3');

export function copyDemoDB(): string {
  mkdirSync(TMP_DIR, { recursive: true });
  copyFileSync(DEMO_DB, TEST_DB);
  return TEST_DB;
}

export function cleanupTestDB(): void {
  for (const path of [TEST_DB, `${TEST_DB}-wal`, `${TEST_DB}-shm`]) {
    if (existsSync(path)) {
      unlinkSync(path);
    }
  }
}

export { TEST_DB, DEMO_DB, TMP_DIR };
