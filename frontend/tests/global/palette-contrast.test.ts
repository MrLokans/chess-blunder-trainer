import { resolve } from 'path';
import { readFileSync } from 'fs';
import { describe, expect, it } from 'vitest';

type Mode = 'light' | 'dark';

const readFn = readFileSync as (path: string, encoding: string) => string;
const resolveFn = resolve as (...args: string[]) => string;
const css = readFn(resolveFn(__dirname as string, '../../../blunder_tutor/web/static/css/tokens.css'), 'utf-8');

function parseRootTokens(source: string): Record<string, string> {
  const start = source.indexOf(':root {');
  const block = source.slice(start, source.indexOf('\n}', start)).replace(/\/\*[\s\S]*?\*\//g, '');
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*([^;]+);/g)].map(m => [m[1], m[2].trim()] as [string, string]));
}

const TOKENS = parseRootTokens(css);

function splitArgs(inner: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = '';
  for (const char of inner) {
    if (char === '(') depth++;
    if (char === ')') depth--;
    if (char === ',' && depth === 0) {
      parts.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  parts.push(current.trim());
  return parts;
}

// --user-* properties are unset by default, so their fallback is what renders. A non-hex
// result makes luminance NaN, which fails every ratio assertion.
function resolveValue(value: string, mode: Mode): string {
  if (value.startsWith('light-dark(')) {
    const [light, dark] = splitArgs(value.slice('light-dark('.length, -1));
    return resolveValue(mode === 'light' ? light : dark, mode);
  }
  if (value.startsWith('var(')) {
    const [name, fallback] = splitArgs(value.slice('var('.length, -1));
    return resolveValue(name.startsWith('--user-') ? fallback : TOKENS[name.slice(2)], mode);
  }
  return value;
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(foreground: string, background: string, mode: Mode): number {
  const [a, b] = [foreground, background].map(token => luminance(resolveValue(TOKENS[token], mode)));
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

const SURFACES = ['surface', 'surface-raised', 'surface-overlay'];
const NEUTRAL_TEXT = ['text', 'text-secondary', 'text-muted'].flatMap(
  text => SURFACES.map(surface => [text, surface] as const),
);
const DARK_ONLY_TEXT = [
  ...['accent', 'info', 'success', 'warning', 'error'].map(status => [status, 'surface-raised'] as const),
  ...['accent', 'success', 'error'].map(fill => ['text-on-accent', fill] as const),
  ...['success-bg', 'warning-bg', 'error-bg', 'info-bg'].map(bg => ['text', bg] as const),
  ['text-inverse', 'surface-inverse'] as const,
  ['selection-text', 'selection-surface'] as const,
];

describe('palette contrast', () => {
  it.each(['light', 'dark'] as const)('%s neutral text meets WCAG AA on every surface', mode => {
    for (const [text, surface] of NEUTRAL_TEXT) {
      expect(contrast(text, surface, mode), `--${text} on --${surface}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('fixed dark status, on-accent and inverse text meets WCAG AA', () => {
    for (const [foreground, background] of DARK_ONLY_TEXT) {
      expect(contrast(foreground, background, 'dark'), `--${foreground} on --${background}`)
        .toBeGreaterThanOrEqual(4.5);
    }
  });

  it.each(['light', 'dark'] as const)('%s controls and chess-side swatches stay distinguishable', mode => {
    expect(contrast('border-control', 'surface-raised', mode)).toBeGreaterThanOrEqual(3);
    expect(contrast('piece-white', 'piece-black', mode)).toBeGreaterThanOrEqual(3);
    expect(luminance(resolveValue(TOKENS['piece-white'], mode)))
      .toBeGreaterThan(luminance(resolveValue(TOKENS['piece-black'], mode)));
  });

  it('keeps the dark palette and chess-side swatches free of custom colours', () => {
    for (const [name, value] of Object.entries(TOKENS)) {
      if (!value.startsWith('light-dark(')) continue;
      expect(splitArgs(value.slice('light-dark('.length, -1))[1], `--${name}`).not.toContain('--user-');
    }
    expect(TOKENS['piece-white']).not.toContain('--user-');
    expect(TOKENS['piece-black']).not.toContain('--user-');
  });
});
