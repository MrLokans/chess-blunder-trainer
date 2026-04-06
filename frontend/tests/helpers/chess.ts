import { resolve } from 'path';
import { readFileSync } from 'fs';
import { vi } from 'vitest';

export function loadChessGlobal(): void {
  const chessPath = resolve(__dirname, '../../../blunder_tutor/web/static/vendor/chess-0.10.3.min.js');
  const code = readFileSync(chessPath, 'utf-8');
  const fn = new Function(code + '\nreturn Chess;');
  vi.stubGlobal('Chess', fn());
}
