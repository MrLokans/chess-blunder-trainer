import { describe, it, expect, vi } from 'vitest';
import { loadChessGlobal } from '../helpers/chess';
import { buildThreatHighlights } from '../../src/trainer/threats';

loadChessGlobal();

describe('buildThreatHighlights', () => {
  it('returns empty map when showThreats is false', () => {
    const game = new Chess();
    expect(buildThreatHighlights(game, false).size).toBe(0);
  });

  it('returns empty map when game is null', () => {
    expect(buildThreatHighlights(null, true).size).toBe(0);
  });

  it('returns empty map for starting position (no hanging pieces)', () => {
    const game = new Chess();
    const result = buildThreatHighlights(game, true);
    expect(result.size).toBe(0);
  });

  it('detects a hanging piece', () => {
    const game = new Chess('rnbqkb1r/ppp2ppp/3p4/4N3/8/8/PPPPPPPP/RNBQKB1R b KQkq - 0 3');
    const result = buildThreatHighlights(game, true);
    expect(result.has('e5')).toBe(true);
    expect(result.get('e5')).toBe('highlight-hanging');
  });

  it('does not flag defended pieces as hanging', () => {
    const game = new Chess('rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2');
    const result = buildThreatHighlights(game, true);
    expect(result.has('f3')).toBe(false);
  });

  it('detects king in check', () => {
    const game = new Chess('4k3/8/8/8/8/8/8/4RK2 b - - 0 1');
    const result = buildThreatHighlights(game, true);
    expect(result.has('e8')).toBe(true);
    expect(result.get('e8')).toBe('highlight-king-danger');
  });

  it('detects checkable king (a check is available)', () => {
    const game = new Chess('7k/8/8/8/8/8/R7/4K3 w - - 0 1');
    const result = buildThreatHighlights(game, true);
    expect(result.has('h8')).toBe(true);
    expect(result.get('h8')).toBe('highlight-checking');
  });

  it('does not double-highlight king in check as checkable', () => {
    const game = new Chess('4k3/8/8/8/8/8/8/4RK2 b - - 0 1');
    const result = buildThreatHighlights(game, true);
    expect(result.get('e8')).toBe('highlight-king-danger');
    expect(result.get('e8')).not.toContain('highlight-checking');
  });
});
