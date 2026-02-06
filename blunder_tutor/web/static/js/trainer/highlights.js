export function buildBlunderHighlight(puzzle) {
  if (!puzzle || !puzzle.blunder_uci || puzzle.blunder_uci.length < 4) return new Map();
  const from = puzzle.blunder_uci.slice(0, 2);
  const to = puzzle.blunder_uci.slice(2, 4);
  return new Map([[from, 'highlight-blunder'], [to, 'highlight-blunder']]);
}

export function buildBestMoveHighlight(puzzle) {
  if (!puzzle || !puzzle.best_move_uci || puzzle.best_move_uci.length < 4) return new Map();
  const from = puzzle.best_move_uci.slice(0, 2);
  const to = puzzle.best_move_uci.slice(2, 4);
  return new Map([[from, 'highlight-best'], [to, 'highlight-best']]);
}

export function buildUserMoveHighlight(uci) {
  if (!uci || uci.length < 4) return new Map();
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  return new Map([[from, 'highlight-user'], [to, 'highlight-user']]);
}

export function buildTacticalHighlights(puzzle, game, bestRevealed, showTactics) {
  if (!showTactics || !bestRevealed || !puzzle || !puzzle.tactical_squares) return new Map();

  const atOriginalPosition = game.fen() === puzzle.fen;
  if (!atOriginalPosition) return new Map();

  const squares = puzzle.tactical_squares;
  const highlights = new Map();
  if (squares.length > 0) {
    highlights.set(squares[0], 'highlight-tactic-primary');
    for (let i = 1; i < squares.length; i++) {
      highlights.set(squares[i], 'highlight-tactic-secondary');
    }
  }
  return highlights;
}

export function mergeHighlights(...maps) {
  const merged = new Map();
  for (const map of maps) {
    for (const [key, value] of map) {
      const existing = merged.get(key);
      merged.set(key, existing ? existing + ' ' + value : value);
    }
  }
  return merged;
}
