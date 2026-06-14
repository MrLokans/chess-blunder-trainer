import { describe, it, expect } from 'vitest';
import {
  applyBoardVisuals,
  arrowsToShapes,
  arrowBrush,
  type BoardArrow,
  type ChessgroundShape,
} from '../../src/shared/board-visuals';
import type { HighlightMap } from '../../src/shared/highlights';

function fakeCg() {
  const calls = {
    set: [] as Record<string, unknown>[],
    autoShapes: [] as ChessgroundShape[][],
  };
  return {
    calls,
    set(config: Record<string, unknown>) { calls.set.push(config); },
    setAutoShapes(shapes: ChessgroundShape[]) { calls.autoShapes.push(shapes); },
  };
}

describe('arrowBrush', () => {
  it('maps known colours to registered brush keys', () => {
    expect(arrowBrush('red')).toBe('red');
    expect(arrowBrush('orange')).toBe('yellow');
    expect(arrowBrush('green')).toBe('green');
  });

  it('falls back to green for unknown colours', () => {
    expect(arrowBrush('chartreuse')).toBe('green');
  });
});

describe('arrowsToShapes', () => {
  it('produces autoShapes with real brush keys', () => {
    const arrows: BoardArrow[] = [{ from: 'e2', to: 'e4', color: 'red' }];
    expect(arrowsToShapes(arrows)).toEqual([{ orig: 'e2', dest: 'e4', brush: 'red' }]);
  });
});

describe('applyBoardVisuals', () => {
  it('applies square highlights via highlight.custom, NOT as autoShape brushes', () => {
    const cg = fakeCg();
    const highlights: HighlightMap = new Map([
      ['e5', 'highlight-hanging'],
      ['e8', 'highlight-king-danger'],
    ]);

    applyBoardVisuals(cg, highlights, []);

    // The whole point of the fix: highlight classes ride on highlight.custom.
    const setArg = cg.calls.set.at(-1);
    const highlight = setArg?.highlight as { custom?: HighlightMap };
    expect(highlight.custom).toBe(highlights);
    expect(highlight.custom?.get('e5')).toBe('highlight-hanging');

    // ...and must never be smuggled in as autoShape brushes (the old, broken path).
    const shapes = cg.calls.autoShapes.at(-1) ?? [];
    const brushes = shapes.map(s => s.brush);
    expect(brushes).not.toContain('highlight-hanging');
    expect(brushes).not.toContain('highlight-king-danger');
    expect(shapes).toHaveLength(0);
  });

  it('clears highlight.custom when there are no highlights', () => {
    const cg = fakeCg();
    applyBoardVisuals(cg, new Map(), []);
    const highlight = cg.calls.set.at(-1)?.highlight as { custom?: HighlightMap };
    expect(highlight.custom).toBeUndefined();
  });

  it('renders arrows as autoShapes with registered brushes', () => {
    const cg = fakeCg();
    const arrows: BoardArrow[] = [{ from: 'd1', to: 'h5', color: 'green' }];
    applyBoardVisuals(cg, new Map(), arrows);
    expect(cg.calls.autoShapes.at(-1)).toEqual([{ orig: 'd1', dest: 'h5', brush: 'green' }]);
  });

  it('preserves lastMove and check highlighting alongside custom squares', () => {
    const cg = fakeCg();
    applyBoardVisuals(cg, new Map([['a1', 'highlight-hanging']]), []);
    const highlight = cg.calls.set.at(-1)?.highlight as Record<string, unknown>;
    expect(highlight.lastMove).toBe(true);
    expect(highlight.check).toBe(true);
  });
});
