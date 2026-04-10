import type { PuzzleData } from './context';

export type HighlightMap = Map<string, string>;

interface GameLike {
  fen(): string;
}

export function buildBlunderHighlight(puzzle: PuzzleData | null): HighlightMap {
  if (!puzzle || !puzzle.blunder_uci || puzzle.blunder_uci.length < 4) return new Map();
  const from = puzzle.blunder_uci.slice(0, 2);
  const to = puzzle.blunder_uci.slice(2, 4);
  return new Map([[from, 'highlight-blunder'], [to, 'highlight-blunder']]);
}

export function buildBestMoveHighlight(puzzle: PuzzleData | null): HighlightMap {
  if (!puzzle || !puzzle.best_move_uci || puzzle.best_move_uci.length < 4) return new Map();
  const from = puzzle.best_move_uci.slice(0, 2);
  const to = puzzle.best_move_uci.slice(2, 4);
  return new Map([[from, 'highlight-best'], [to, 'highlight-best']]);
}

export function buildUserMoveHighlight(uci: string | null): HighlightMap {
  if (!uci || uci.length < 4) return new Map();
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  return new Map([[from, 'highlight-user'], [to, 'highlight-user']]);
}

export function buildTacticalHighlights(
  puzzle: PuzzleData | null,
  game: GameLike | null,
  bestRevealed: boolean,
  showTactics: boolean,
): HighlightMap {
  if (!showTactics || !bestRevealed || !puzzle || puzzle.tactical_squares.length === 0) return new Map();

  const atOriginalPosition = game !== null && game.fen() === puzzle.fen;
  if (!atOriginalPosition) return new Map();

  const squares = puzzle.tactical_squares;
  const highlights: HighlightMap = new Map();
  if (squares.length > 0) {
    const primary = squares[0];
    if (primary) highlights.set(primary, 'highlight-tactic-primary');
    for (let i = 1; i < squares.length; i++) {
      const sq = squares[i];
      if (sq) highlights.set(sq, 'highlight-tactic-secondary');
    }
  }
  return highlights;
}

export function mergeHighlights(...maps: HighlightMap[]): HighlightMap {
  const merged: HighlightMap = new Map();
  for (const map of maps) {
    for (const [key, value] of map) {
      const existing = merged.get(key);
      merged.set(key, existing ? existing + ' ' + value : value);
    }
  }
  return merged;
}
