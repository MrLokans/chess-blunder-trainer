import { resolve } from 'path';
import { readFileSync } from 'fs';
import { vi } from 'vitest';

export function loadChessGlobal(): void {
  const resolveFn = resolve as (...args: string[]) => string;
  const readFn = readFileSync as (path: string, encoding: string) => string;
  const dir = __dirname as string;
  const chessPath = resolveFn(dir, '../../../blunder_tutor/web/static/vendor/chess-0.10.3.min.js');
  const code = readFn(chessPath, 'utf-8');
  // eslint-disable-next-line @typescript-eslint/no-implied-eval -- dynamically loading vendored Chess library for tests
  const fn = new Function(code + '\nreturn Chess;') as () => unknown;
  vi.stubGlobal('Chess', fn());
}
