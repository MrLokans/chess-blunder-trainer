import { afterEach, describe, expect, it, vi } from 'vitest';
import { boardAnimation, scrollBehavior } from '../../src/shared/motion';

function mockReducedMotion(reduce: boolean): void {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({ matches: reduce && query.includes('reduce') })));
}

describe('motion preferences', () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it('animates board pieces and scrolls smoothly by default', () => {
    mockReducedMotion(false);
    expect(boardAnimation(150)).toEqual({ enabled: true, duration: 150 });
    expect(scrollBehavior()).toBe('smooth');
  });

  it('disables piece sliding and smooth scrolling when reduced motion is requested', () => {
    mockReducedMotion(true);
    expect(boardAnimation(350)).toEqual({ enabled: false, duration: 350 });
    expect(scrollBehavior()).toBe('auto');
  });
});
