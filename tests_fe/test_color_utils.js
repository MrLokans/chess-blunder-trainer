import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { adjustColor } from '../blunder_tutor/web/static/js/color-utils.js';

describe('adjustColor', () => {
  it('returns a 7-char hex string', () => {
    const result = adjustColor('#4f6d7a', 50);
    assert.match(result, /^#[0-9a-f]{6}$/);
  });

  it('lightness=0 returns black', () => {
    const result = adjustColor('#ff0000', 0);
    assert.equal(result, '#000000');
  });

  it('lightness=100 returns white', () => {
    const result = adjustColor('#ff0000', 100);
    assert.equal(result, '#ffffff');
  });

  it('preserves hue when adjusting lightness', () => {
    const light = adjustColor('#0000ff', 70);
    const r = parseInt(light.slice(1, 3), 16);
    const g = parseInt(light.slice(3, 5), 16);
    const b = parseInt(light.slice(5, 7), 16);
    assert(b > r, 'blue channel should dominate');
    assert(b > g, 'blue channel should dominate');
  });

  it('saturation=0 produces grayscale', () => {
    const result = adjustColor('#ff0000', null, 0);
    const r = parseInt(result.slice(1, 3), 16);
    const g = parseInt(result.slice(3, 5), 16);
    const b = parseInt(result.slice(5, 7), 16);
    assert.equal(r, g);
    assert.equal(g, b);
  });

  it('handles pure gray input', () => {
    const result = adjustColor('#808080', 50);
    assert.match(result, /^#[0-9a-f]{6}$/);
  });

  it('handles white input', () => {
    const result = adjustColor('#ffffff', 50);
    assert.match(result, /^#[0-9a-f]{6}$/);
  });

  it('handles black input', () => {
    const result = adjustColor('#000000', 50);
    assert.equal(result, '#808080');
  });
});
