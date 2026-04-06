import { describe, it, expect } from 'vitest';
import {
  buildBlunderHighlight,
  buildBestMoveHighlight,
  buildUserMoveHighlight,
  buildTacticalHighlights,
  mergeHighlights,
} from '../../src/trainer/highlights';
import type { PuzzleData } from '../../src/trainer/state';

function makePuzzle(overrides: Partial<PuzzleData> = {}): PuzzleData {
  return {
    game_id: 'test',
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    ply: 1,
    blunder_uci: '',
    blunder_san: '',
    best_move_uci: '',
    best_move_san: '',
    best_line: [],
    player_color: 'white',
    eval_before: 0,
    eval_after: 0,
    eval_before_display: '0.0',
    eval_after_display: '0.0',
    cp_loss: 0,
    game_phase: 'opening',
    tactical_pattern: null,
    tactical_reason: null,
    tactical_squares: [],
    explanation_blunder: null,
    explanation_best: null,
    game_url: null,
    difficulty: 'medium',
    pre_move_uci: null,
    pre_move_fen: null,
    best_move_eval: null,
    ...overrides,
  };
}

describe('buildBlunderHighlight', () => {
  it('returns empty map for null puzzle', () => {
    expect(buildBlunderHighlight(null).size).toBe(0);
  });

  it('returns empty map for missing blunder_uci', () => {
    expect(buildBlunderHighlight(makePuzzle()).size).toBe(0);
  });

  it('returns empty map for short UCI string', () => {
    expect(buildBlunderHighlight(makePuzzle({ blunder_uci: 'e2' })).size).toBe(0);
  });

  it('highlights from and to squares', () => {
    const result = buildBlunderHighlight(makePuzzle({ blunder_uci: 'e2e4' }));
    expect(result.size).toBe(2);
    expect(result.get('e2')).toBe('highlight-blunder');
    expect(result.get('e4')).toBe('highlight-blunder');
  });

  it('handles promotion UCI (5 chars)', () => {
    const result = buildBlunderHighlight(makePuzzle({ blunder_uci: 'e7e8q' }));
    expect(result.size).toBe(2);
    expect(result.get('e7')).toBe('highlight-blunder');
    expect(result.get('e8')).toBe('highlight-blunder');
  });
});

describe('buildBestMoveHighlight', () => {
  it('returns empty map for null puzzle', () => {
    expect(buildBestMoveHighlight(null).size).toBe(0);
  });

  it('returns empty map for missing best_move_uci', () => {
    expect(buildBestMoveHighlight(makePuzzle()).size).toBe(0);
  });

  it('highlights from and to squares', () => {
    const result = buildBestMoveHighlight(makePuzzle({ best_move_uci: 'd2d4' }));
    expect(result.size).toBe(2);
    expect(result.get('d2')).toBe('highlight-best');
    expect(result.get('d4')).toBe('highlight-best');
  });
});

describe('buildUserMoveHighlight', () => {
  it('returns empty map for null UCI', () => {
    expect(buildUserMoveHighlight(null).size).toBe(0);
  });

  it('returns empty map for empty string', () => {
    expect(buildUserMoveHighlight('').size).toBe(0);
  });

  it('returns empty map for short UCI', () => {
    expect(buildUserMoveHighlight('e2').size).toBe(0);
  });

  it('highlights from and to squares', () => {
    const result = buildUserMoveHighlight('g1f3');
    expect(result.size).toBe(2);
    expect(result.get('g1')).toBe('highlight-user');
    expect(result.get('f3')).toBe('highlight-user');
  });
});

describe('buildTacticalHighlights', () => {
  const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  it('returns empty map when showTactics is false', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: ['e4', 'e5'] });
    const game = { fen: () => fen } as unknown as ChessInstance;
    expect(buildTacticalHighlights(puzzle, game, true, false).size).toBe(0);
  });

  it('returns empty map when bestRevealed is false', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: ['e4', 'e5'] });
    const game = { fen: () => fen } as unknown as ChessInstance;
    expect(buildTacticalHighlights(puzzle, game, false, true).size).toBe(0);
  });

  it('returns empty map when puzzle is null', () => {
    const game = { fen: () => fen } as unknown as ChessInstance;
    expect(buildTacticalHighlights(null, game, true, true).size).toBe(0);
  });

  it('returns empty map when tactical_squares is missing', () => {
    const puzzle = makePuzzle({ fen });
    const game = { fen: () => fen } as unknown as ChessInstance;
    expect(buildTacticalHighlights(puzzle, game, true, true).size).toBe(0);
  });

  it('returns empty map when not at original position', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: ['e4'] });
    const game = { fen: () => 'different fen' } as unknown as ChessInstance;
    expect(buildTacticalHighlights(puzzle, game, true, true).size).toBe(0);
  });

  it('marks first square as primary, rest as secondary', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: ['e4', 'd5', 'f6'] });
    const game = { fen: () => fen } as unknown as ChessInstance;
    const result = buildTacticalHighlights(puzzle, game, true, true);
    expect(result.size).toBe(3);
    expect(result.get('e4')).toBe('highlight-tactic-primary');
    expect(result.get('d5')).toBe('highlight-tactic-secondary');
    expect(result.get('f6')).toBe('highlight-tactic-secondary');
  });

  it('handles single tactical square', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: ['e4'] });
    const game = { fen: () => fen } as unknown as ChessInstance;
    const result = buildTacticalHighlights(puzzle, game, true, true);
    expect(result.size).toBe(1);
    expect(result.get('e4')).toBe('highlight-tactic-primary');
  });

  it('returns empty map for empty tactical_squares array', () => {
    const puzzle = makePuzzle({ fen, tactical_squares: [] });
    const game = { fen: () => fen } as unknown as ChessInstance;
    expect(buildTacticalHighlights(puzzle, game, true, true).size).toBe(0);
  });
});

describe('mergeHighlights', () => {
  it('returns empty map for no inputs', () => {
    expect(mergeHighlights().size).toBe(0);
  });

  it('returns single map unchanged', () => {
    const m = new Map([['e4', 'highlight-blunder']]);
    const result = mergeHighlights(m);
    expect(result.get('e4')).toBe('highlight-blunder');
  });

  it('merges non-overlapping maps', () => {
    const a = new Map([['e2', 'highlight-blunder']]);
    const b = new Map([['d4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    expect(result.size).toBe(2);
    expect(result.get('e2')).toBe('highlight-blunder');
    expect(result.get('d4')).toBe('highlight-best');
  });

  it('concatenates CSS classes for overlapping squares', () => {
    const a = new Map([['e4', 'highlight-blunder']]);
    const b = new Map([['e4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    expect(result.size).toBe(1);
    expect(result.get('e4')).toBe('highlight-blunder highlight-best');
  });

  it('concatenates multiple overlapping highlights', () => {
    const a = new Map([['e4', 'highlight-blunder']]);
    const b = new Map([['e4', 'highlight-best']]);
    const c = new Map([['e4', 'highlight-user']]);
    const result = mergeHighlights(a, b, c);
    expect(result.get('e4')).toBe('highlight-blunder highlight-best highlight-user');
  });

  it('handles empty maps gracefully', () => {
    const a = new Map<string, string>();
    const b = new Map([['e4', 'highlight-best']]);
    const result = mergeHighlights(a, b);
    expect(result.size).toBe(1);
    expect(result.get('e4')).toBe('highlight-best');
  });
});
