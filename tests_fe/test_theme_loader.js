import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// theme-loader.js is an IIFE that sets window.adjustColor and window.applyTheme
// It also reads localStorage and document.documentElement — we need to mock those

globalThis.window = globalThis.window || {};
globalThis.localStorage = {
  _store: {},
  getItem(k) { return this._store[k] ?? null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; },
  clear() { this._store = {}; },
};

const cssVars = {};
globalThis.document = {
  documentElement: {
    style: {
      setProperty(k, v) { cssVars[k] = v; },
    },
  },
};

// Load the module
await import('../blunder_tutor/web/static/js/theme-loader.js');

const adjustColor = globalThis.window.adjustColor;
const applyTheme = globalThis.window.applyTheme;

describe('adjustColor', () => {
  it('returns a 7-char hex string', () => {
    const result = adjustColor('#FF0000', 50);
    assert.match(result, /^#[0-9a-f]{6}$/);
  });

  it('returns pure black at lightness 0', () => {
    const result = adjustColor('#FF0000', 0);
    assert.equal(result, '#000000');
  });

  it('returns pure white at lightness 100', () => {
    const result = adjustColor('#FF0000', 100);
    assert.equal(result, '#ffffff');
  });

  it('returns gray for 50% lightness with zero saturation', () => {
    const result = adjustColor('#FF0000', 50, 0);
    assert.equal(result, '#808080');
  });

  it('preserves hue when only changing lightness', () => {
    const lighter = adjustColor('#0000FF', 70);
    // Should still be bluish
    const r = parseInt(lighter.slice(1, 3), 16);
    const b = parseInt(lighter.slice(5, 7), 16);
    assert.ok(b > r, `Expected blue channel (${b}) > red channel (${r})`);
  });

  it('handles pure white input', () => {
    const result = adjustColor('#FFFFFF', 50);
    assert.match(result, /^#[0-9a-f]{6}$/);
  });

  it('handles pure black input', () => {
    const result = adjustColor('#000000', 50);
    // Black has no hue/saturation, so adjusting lightness to 50 gives gray
    assert.equal(result, '#808080');
  });

  it('preserves color when not adjusting lightness or saturation', () => {
    // adjustColor with no lightness/saturation adjustment should return
    // a color close to the original (HSL round-trip)
    const original = '#1A3A8F';
    const result = adjustColor(original);
    // Allow small rounding differences
    const origR = parseInt(original.slice(1, 3), 16);
    const origG = parseInt(original.slice(3, 5), 16);
    const origB = parseInt(original.slice(5, 7), 16);
    const resR = parseInt(result.slice(1, 3), 16);
    const resG = parseInt(result.slice(3, 5), 16);
    const resB = parseInt(result.slice(5, 7), 16);
    assert.ok(Math.abs(origR - resR) <= 1, `Red: ${origR} vs ${resR}`);
    assert.ok(Math.abs(origG - resG) <= 1, `Green: ${origG} vs ${resG}`);
    assert.ok(Math.abs(origB - resB) <= 1, `Blue: ${origB} vs ${resB}`);
  });

  it('desaturates when saturation set to 0', () => {
    const result = adjustColor('#FF0000', undefined, 0);
    // Red with 0 saturation should be a gray at the same lightness
    const r = parseInt(result.slice(1, 3), 16);
    const g = parseInt(result.slice(3, 5), 16);
    const b = parseInt(result.slice(5, 7), 16);
    assert.equal(r, g);
    assert.equal(g, b);
  });
});

describe('applyTheme', () => {
  beforeEach(() => {
    for (const key of Object.keys(cssVars)) {
      delete cssVars[key];
    }
  });

  it('sets primary CSS variables', () => {
    applyTheme({ primary: '#1A3A8F' });
    assert.equal(cssVars['--color-primary'], '#1A3A8F');
    assert.ok(cssVars['--color-primary-hover']);
    assert.ok(cssVars['--color-primary-muted']);
    assert.equal(cssVars['--accent'], '#1A3A8F');
  });

  it('sets success CSS variables with derived bg and border', () => {
    applyTheme({ success: '#2D8F3E' });
    assert.equal(cssVars['--color-success'], '#2D8F3E');
    assert.ok(cssVars['--color-success-bg']);
    assert.ok(cssVars['--color-success-border']);
    assert.equal(cssVars['--success'], '#2D8F3E');
  });

  it('sets error CSS variables', () => {
    applyTheme({ error: '#D42828' });
    assert.equal(cssVars['--color-error'], '#D42828');
    assert.equal(cssVars['--error'], '#D42828');
  });

  it('sets warning CSS variables', () => {
    applyTheme({ warning: '#F2C12E' });
    assert.equal(cssVars['--color-warning'], '#F2C12E');
    assert.equal(cssVars['--warning'], '#F2C12E');
  });

  it('sets phase colors', () => {
    applyTheme({
      phase_opening: '#AA0000',
      phase_middlegame: '#00AA00',
      phase_endgame: '#0000AA',
    });
    assert.equal(cssVars['--color-phase-opening'], '#AA0000');
    assert.equal(cssVars['--color-phase-middlegame'], '#00AA00');
    assert.equal(cssVars['--color-phase-endgame'], '#0000AA');
  });

  it('sets heatmap colors', () => {
    applyTheme({
      heatmap_empty: '#ebedf0',
      heatmap_l1: '#9be9a8',
      heatmap_l2: '#40c463',
      heatmap_l3: '#30a14e',
      heatmap_l4: '#216e39',
    });
    assert.equal(cssVars['--heatmap-empty'], '#ebedf0');
    assert.equal(cssVars['--heatmap-l4'], '#216e39');
  });

  it('sets background and text semantic aliases', () => {
    applyTheme({ bg: '#FFFFFF', bg_card: '#F5F5F5', text: '#111111', text_muted: '#666666' });
    assert.equal(cssVars['--bg'], '#FFFFFF');
    assert.equal(cssVars['--bg-elevated'], '#F5F5F5');
    assert.equal(cssVars['--card-bg'], '#F5F5F5');
    assert.equal(cssVars['--text'], '#111111');
    assert.equal(cssVars['--text-muted'], '#666666');
  });

  it('skips unset properties without error', () => {
    assert.doesNotThrow(() => applyTheme({}));
  });
});
