function getAttackers(gameObj, square, byColor) {
  const attackers = [];
  const testGame = new Chess(gameObj.fen());

  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const piece = testGame.get(sq);
      if (piece && piece.color === byColor) {
        const moves = testGame.moves({ square: sq, verbose: true });
        for (const move of moves) {
          if (move.to === square) {
            attackers.push({ square: sq, piece: piece });
            break;
          }
        }
      }
    }
  }
  return attackers;
}

function getDefenders(gameObj, square, piece) {
  const testGame = new Chess(gameObj.fen());
  const defenderColor = piece.color;

  testGame.remove(square);

  const defenders = [];
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const p = testGame.get(sq);
      if (p && p.color === defenderColor) {
        const moves = testGame.moves({ square: sq, verbose: true });
        for (const move of moves) {
          if (move.to === square) {
            defenders.push({ square: sq, piece: p });
            break;
          }
        }
      }
    }
  }
  return defenders;
}

function findHangingPieces(gameObj) {
  const hanging = [];
  const files = 'abcdefgh';

  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const piece = gameObj.get(sq);
      if (piece && piece.type !== 'k') {
        const attackers = getAttackers(gameObj, sq, piece.color === 'w' ? 'b' : 'w');
        if (attackers.length > 0) {
          const defenders = getDefenders(gameObj, sq, piece);
          if (defenders.length === 0) {
            hanging.push(sq);
          }
        }
      }
    }
  }
  return hanging;
}

function findKingInCheck(gameObj) {
  if (gameObj.in_check()) {
    const turnColor = gameObj.turn();
    const files = 'abcdefgh';
    for (let f = 0; f < 8; f++) {
      for (let r = 1; r <= 8; r++) {
        const sq = files[f] + r;
        const piece = gameObj.get(sq);
        if (piece && piece.type === 'k' && piece.color === turnColor) {
          return sq;
        }
      }
    }
  }
  return null;
}

function findCheckableKing(gameObj) {
  const moves = gameObj.moves({ verbose: true });
  for (const move of moves) {
    const testGame = new Chess(gameObj.fen());
    testGame.move(move);
    if (testGame.in_check()) {
      const oppColor = gameObj.turn() === 'w' ? 'b' : 'w';
      const files = 'abcdefgh';
      for (let f = 0; f < 8; f++) {
        for (let r = 1; r <= 8; r++) {
          const sq = files[f] + r;
          const piece = testGame.get(sq);
          if (piece && piece.type === 'k' && piece.color === oppColor) {
            return sq;
          }
        }
      }
    }
  }
  return null;
}

export function buildThreatHighlights(game, showThreats) {
  const highlights = new Map();
  if (!showThreats || !game) return highlights;

  const hanging = findHangingPieces(game);
  for (const sq of hanging) {
    highlights.set(sq, 'highlight-hanging');
  }

  const kingInCheck = findKingInCheck(game);
  if (kingInCheck) {
    highlights.set(kingInCheck, 'highlight-king-danger');
  }

  const checkableKing = findCheckableKing(game);
  if (checkableKing && checkableKing !== kingInCheck) {
    highlights.set(checkableKing, 'highlight-checking');
  }

  return highlights;
}
