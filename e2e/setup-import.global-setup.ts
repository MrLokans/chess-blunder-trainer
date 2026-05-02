import { execSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Mirror of `auth.global-setup.ts` for the setup-and-import surface:
 * read the invite the app's `_bootstrap_auth` already wrote during
 * lifespan startup and stash it where the test can pick it up. Lives
 * under a sibling tmp dir so the two suites can coexist on disk
 * without racing over `auth.sqlite3`.
 */
export default function globalSetup(): void {
  const projectRoot = resolve(__dirname, '..');
  const tmpDir = resolve(__dirname, '.tmp-setup-import');
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
  rmSync(resolve(tmpDir, 'users'), { recursive: true, force: true });
}
