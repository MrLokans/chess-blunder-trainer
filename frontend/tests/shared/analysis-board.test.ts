import { describe, it, expect } from 'vitest';
import { loadChessGlobal } from '../helpers/chess';
import { buildDests } from '../../src/shared/analysis-board';

loadChessGlobal();

describe('buildDests', () => {
  it('maps each from-square to its legal destinations from the start position', () => {
    const game = new Chess();
    const dests = buildDests(game);
    expect(dests.get('e2')).toContain('e4');
    expect(dests.get('g1')).toEqual(expect.arrayContaining(['f3', 'h3']));
    expect(dests.has('e4')).toBe(false);
  });
});
