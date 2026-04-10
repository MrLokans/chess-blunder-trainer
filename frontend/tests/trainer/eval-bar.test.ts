import { describe, it, expect } from 'vitest';
import { updateEvalBar } from '../../src/shared/eval-bar';

function makeMockEl(): HTMLElement {
  return { style: { height: '' }, textContent: '', className: '' } as unknown as HTMLElement;
}

describe('updateEvalBar', () => {
  it('shows +0.0 at equal position', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(0, 'white', fill, value);
    expect(value.textContent).toBe('+0.0');
    expect(fill.style.height).toBe('50%');
    expect(value.className).toBe('eval-value positive');
  });

  it('shows positive eval for white advantage as white', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(200, 'white', fill, value);
    expect(value.textContent).toBe('+2.0');
    expect(parseFloat(fill.style.height)).toBeGreaterThan(50);
    expect(value.className).toBe('eval-value positive');
  });

  it('flips perspective for black player', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(200, 'black', fill, value);
    expect(parseFloat(fill.style.height)).toBeLessThan(50);
    expect(value.className).toBe('eval-value negative');
  });

  it('clamps extreme values', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(9999, 'white', fill, value);
    expect(fill.style.height).toBe('100%');
  });

  it('displays mate symbol for very large values', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(10001, 'white', fill, value);
    expect(value.textContent).toBe('+M');
  });

  it('displays negative mate symbol', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(-10001, 'white', fill, value);
    expect(value.textContent).toBe('-M');
  });

  it('handles negative eval', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(-150, 'white', fill, value);
    expect(value.textContent).toBe('-1.5');
    expect(parseFloat(fill.style.height)).toBeLessThan(50);
    expect(value.className).toBe('eval-value negative');
  });
});
