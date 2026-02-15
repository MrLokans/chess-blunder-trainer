import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  buildBlunderHighlight, buildBestMoveHighlight, buildUserMoveHighlight,
  buildTacticalHighlights, mergeHighlights,
} from '../blunder_tutor/web/static/js/trainer/highlights.js';

describe('buildBlunderHighlight', () => {
  it('returns empty map for null puzzle', () => {
    assert.equal(buildBlunderHighlight(null).size, 0);
  });

  it('returns empty map for missing blunder_uci', () => {
    assert.equal(buildBlunderHighlight({}).size, 0);
  });

  it('returns empty map for short UCI string', () => {
    assert.equal(buildBlunderHighlight({ blunder_uci: 'e2' }).size, 0);
  });

  it('highlights from and to squares', () => {
    const result = buildBlunderHighlight({ blunder_uci: 'e2e4' });
    assert.equal(result.size, 2);
    assert.equal(result.get('e2'), 'highlight-blunder');
    assert.equal(result.get('e4'), 'highlight-blunder');
  });

  it('handles promotion UCI (5 chars)', () => {
    const result = buildBlunderHighlight({ blunder_uci: 'e7e8q' });
    assert.equal(result.size, 2);
    assert.equal(result.get('e7'), 'highlight-blunder');
    assert.equal(result.get('e8'), 'highlight-blunder');
  });
});

describe('buildBestMoveHighlight', () => {
  it('returns empty map for null puzzle', () => {
    assert.equal(buildBestMoveHighlight(null).size, 0);
  });

  it('returns empty map for missing best_move_uci', () => {
    assert.equal(buildBestMoveHighlight({}).size, 0);
  });

  it('highlights from and to squares', () => {
    const result = buildBestMoveHighlight({ best_move_uci: 'd2d4' });
    assert.equal(result.size, 2);
    assert.equal(result.get('d2'), 'highlight-best');
    assert.equal(result.get('d4'), 'highlight-best');
  });
});

describe('buildUserMoveHighlight', () => {
  it('returns empty map for null UCI', () => {
    assert.equal(buildUserMoveHighlight(null).size, 0);
  });

  it('returns empty map for empty string', () => {
    assert.equal(buildUserMoveHighlight('').size, 0);
  });

  it('returns empty map for short UCI', () => {
    assert.equal(buildUserMoveHighlight('e2').size, 0);
  });

  it('highlights from and to squares', () => {
    const result = buildUserMoveHighlight('g1f3');
    assert.equal(result.size, 2);
    assert.equal(result.get('g1'), 'highlight-user');
    assert.equal(result.get('f3'), 'highlight-user');
  });
});

describe('buildTacticalHighlights', () => {
  const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  it('returns empty map when showTactics is false', () => {
    const puzzle = { fen, tactical_squares: ['e4', 'e5'] };
    const game = { fen: () => fen };
    assert.equal(buildTacticalHighlights(puzzle, game, true, false).size, 0);
  });

  it('returns empty map when bestRevealed is false', () => {
    const puzzle = { fen, tactical_squares: ['e4', 'e5'] };
    const game = { fen: () => fen };
    assert.equal(buildTacticalHighlights(puzzle, game, false, true).size, 0);
  });

  it('returns empty map when puzzle is null', () => {
    const game = { fen: () => fen };
    assert.equal(buildTacticalHighlights(null, game, true, true).size, 0);
  });

  it('returns empty map when tactical_squares is missing', () => {
    const puzzle = { fen };
    const game = { fen: () => fen };
    assert.equal(buildTacticalHighlights(puzzle, game, true, true).size, 0);
  });

  it('returns empty map when not at original position', () => {
    const puzzle = { fen, tactical_squares: ['e4'] };
    const game = { fen: () => 'different fen' };
    assert.equal(buildTacticalHighlights(puzzle, game, true, true).size, 0);
  });

  it('marks first square as primary, rest as secondary', () => {
    const puzzle = { fen, tactical_squares: ['e4', 'd5', 'f6'] };
    const game = { fen: () => fen };
    const result = buildTacticalHighlights(puzzle, game, true, true);
    assert.equal(result.size, 3);
    assert.equal(result.get('e4'), 'highlight-tactic-primary');
    assert.equal(result.get('d5'), 'highlight-tactic-secondary');
    assert.equal(result.get('f6'), 'highlight-tactic-secondary');
  });

  it('handles single tactical square', () => {
    const puzzle = { fen, tactical_squares: ['e4'] };
    const game = { fen: () => fen };
    const result = buildTacticalHighlights(puzzle, game, true, true);
    assert.equal(result.size, 1);
    assert.equal(result.get('e4'), 'highlight-tactic-primary');
  });

  it('returns empty map for empty tactical_squares array', () => {
    const puzzle = { fen, tactical_squares: [] };
    const game = { fen: () => fen };
    assert.equal(buildTacticalHighlights(puzzle, game, true, true).size, 0);
  });
});

describe('mergeHighlights', () => {
  it('returns empty map for no inputs', () => {
    assert.equal(mergeHighlights().size, 0);
  });

  it('returns single map unchanged', () => {
    const m = new Map([['e4', 'highlight-blunder']]);
    const result = mergeHighlights(m);
    assert.equal(result.get('e4'), 'highlight-blunder');
  });

  it('merges non-overlapping maps', () => {
    const a = new Map([['e2', 'highlight-blunder']]);
    const b = new Map([['d4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    assert.equal(result.size, 2);
    assert.equal(result.get('e2'), 'highlight-blunder');
    assert.equal(result.get('d4'), 'highlight-best');
  });

  it('concatenates CSS classes for overlapping squares', () => {
    const a = new Map([['e4', 'highlight-blunder']]);
    const b = new Map([['e4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    assert.equal(result.size, 1);
    assert.equal(result.get('e4'), 'highlight-blunder highlight-best');
  });

  it('concatenates multiple overlapping highlights', () => {
    const a = new Map([['e4', 'highlight-blunder']]);
    const b = new Map([['e4', 'highlight-best']]);
    const c = new Map([['e4', 'highlight-user']]);
    const result = mergeHighlights(a, b, c);
    assert.equal(result.get('e4'), 'highlight-blunder highlight-best highlight-user');
  });

  it('handles empty maps gracefully', () => {
    const a = new Map();
    const b = new Map([['e4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    assert.equal(result.size, 1);
    assert.equal(result.get('e4'), 'highlight-best');
  });
});
