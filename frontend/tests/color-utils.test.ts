import { describe, it, expect } from 'vitest';
import { adjustColor } from '../src/global/theme-loader';

describe('adjustColor', () => {
  it('returns a 7-char hex string', () => {
    const result = adjustColor('#4f6d7a', 50);
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
  });

  it('lightness=0 returns black', () => {
    const result = adjustColor('#ff0000', 0);
    expect(result).toBe('#000000');
  });

  it('lightness=100 returns white', () => {
    const result = adjustColor('#ff0000', 100);
    expect(result).toBe('#ffffff');
  });

  it('preserves hue when adjusting lightness', () => {
    const light = adjustColor('#0000ff', 70);
    const r = parseInt(light.slice(1, 3), 16);
    const g = parseInt(light.slice(3, 5), 16);
    const b = parseInt(light.slice(5, 7), 16);
    expect(b).toBeGreaterThan(r);
    expect(b).toBeGreaterThan(g);
  });

  it('saturation=0 produces grayscale', () => {
    const result = adjustColor('#ff0000', null, 0);
    const r = parseInt(result.slice(1, 3), 16);
    const g = parseInt(result.slice(3, 5), 16);
    const b = parseInt(result.slice(5, 7), 16);
    expect(r).toBe(g);
    expect(g).toBe(b);
  });

  it('handles pure gray input', () => {
    const result = adjustColor('#808080', 50);
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
  });

  it('handles white input', () => {
    const result = adjustColor('#ffffff', 50);
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
  });

  it('handles black input', () => {
    const result = adjustColor('#000000', 50);
    expect(result).toBe('#808080');
  });
});
