import { execSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Reads the invite code the app's `_bootstrap_auth` generates during
 * lifespan startup and writes it to `.tmp-auth/invite.txt` for the
 * test to pick up.
 *
 * Why not pre-seed the DB ourselves: Playwright starts `webServer`
 * before `globalSetup` runs. If we wipe `.tmp-auth/` in globalSetup
 * after the app has already opened `auth.sqlite3`, the app keeps
 * reading from the now-unlinked inode while we write a fresh DB with
 * a new invite. The app and the test then disagree. Letting the app
 * own the DB and having globalSetup observe it avoids the race.
 *
 * The webServer URL probe (`/health`) is already complete by the
 * time globalSetup runs, so `_bootstrap_auth` has finished and the
 * invite row is guaranteed to exist.
 */
export default function globalSetup(): void {
  const projectRoot = resolve(__dirname, '..');
  const tmpDir = resolve(__dirname, '.tmp-auth');
  mkdirSync(tmpDir, { recursive: true });

  const authDbPath = resolve(tmpDir, 'auth.sqlite3');
  const readScript = resolve(projectRoot, 'scripts', 'bootstrap_auth_db.py');

  const invite = execSync(
    `uv run python "${readScript}" "${authDbPath}"`,
    { cwd: projectRoot, encoding: 'utf-8' },
  ).trim();

  if (!invite) {
    throw new Error(
      'Bootstrap script produced an empty invite code — the app may ' +
      'have failed to start, or `_bootstrap_auth` did not run.',
    );
  }

  writeFileSync(resolve(tmpDir, 'invite.txt'), invite);
  // Clean up stale user-data dirs from prior runs so tests start with
  // exactly one user row (the one they create) and zero orphan dirs.
  rmSync(resolve(tmpDir, 'users'), { recursive: true, force: true });
}
