export function highlightSquare(square, className) {
  const squareEl = document.querySelector(`.square-${square}`);
  if (squareEl) {
    squareEl.classList.add(className);
  }
}

export function highlightMove(uci, type) {
  if (!uci || uci.length < 4) return;
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  highlightSquare(from, `highlight-${type}-from`);
  highlightSquare(to, `highlight-${type}-to`);
}

export function clearHighlights() {
  document.querySelectorAll('.highlight-blunder-from, .highlight-blunder-to, .highlight-best-from, .highlight-best-to, .highlight-user-from, .highlight-user-to').forEach(el => {
    el.classList.remove('highlight-blunder-from', 'highlight-blunder-to', 'highlight-best-from', 'highlight-best-to', 'highlight-user-from', 'highlight-user-to');
  });
}

export function clearLegalMoveHighlights() {
  document.querySelectorAll('.highlight-legal-move, .highlight-legal-capture').forEach(el => {
    el.classList.remove('highlight-legal-move', 'highlight-legal-capture');
  });
}

export function highlightLegalMoves(game, square) {
  if (!game) return;

  const moves = game.moves({ square: square, verbose: true });
  for (const move of moves) {
    const targetPiece = game.get(move.to);
    if (targetPiece) {
      highlightSquare(move.to, 'highlight-legal-capture');
    } else {
      highlightSquare(move.to, 'highlight-legal-move');
    }
  }
}

export function showBlunderHighlight(puzzle) {
  if (!puzzle || !puzzle.blunder_uci) return;
  highlightMove(puzzle.blunder_uci, 'blunder');
}

export function showBestMoveHighlight(puzzle) {
  if (!puzzle || !puzzle.best_move_uci) return;
  highlightMove(puzzle.best_move_uci, 'best');
}

export function showUserMoveHighlight(uci) {
  if (!uci) return;
  highlightMove(uci, 'user');
}

export function clearTacticalHighlights() {
  document.querySelectorAll('.highlight-tactic-primary, .highlight-tactic-secondary').forEach(el => {
    el.classList.remove('highlight-tactic-primary', 'highlight-tactic-secondary');
  });
}

export function drawTacticalHighlights(puzzle, game, bestRevealed, showTactics, legendTactic) {
  clearTacticalHighlights();

  if (!showTactics) return;
  if (!bestRevealed || !puzzle || !puzzle.tactical_squares) return;

  const atOriginalPosition = game.fen() === puzzle.fen;
  if (!atOriginalPosition) return;

  const squares = puzzle.tactical_squares;
  if (squares.length > 0) {
    highlightSquare(squares[0], 'highlight-tactic-primary');

    for (let i = 1; i < squares.length; i++) {
      highlightSquare(squares[i], 'highlight-tactic-secondary');
    }

    if (legendTactic) {
      legendTactic.style.display = 'flex';
    }
  }
}
