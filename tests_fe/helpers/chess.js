import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const code = readFileSync(
  join(__dirname, '../../blunder_tutor/web/static/vendor/chess-0.10.3.min.js'),
  'utf8',
);

const mod = {};
new Function('exports', 'module', code)(mod, { exports: mod });

export const Chess = mod.Chess;
