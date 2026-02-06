function getSquareCenter(square, boardEl, orientation) {
  const files = 'abcdefgh';
  const file = files.indexOf(square[0]);
  const rank = parseInt(square[1]) - 1;

  const boardRect = boardEl.getBoundingClientRect();
  const squareSize = boardRect.width / 8;

  let x, y;
  if (orientation === 'white') {
    x = (file + 0.5) * squareSize;
    y = (7 - rank + 0.5) * squareSize;
  } else {
    x = (7 - file + 0.5) * squareSize;
    y = (rank + 0.5) * squareSize;
  }

  return { x, y };
}

function createArrowSVG(arrows, boardEl, orientation) {
  const boardRect = boardEl.getBoundingClientRect();
  const width = boardRect.width;
  const height = boardRect.height;

  let svg = `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">`;

  svg += `
    <defs>
      <marker id="arrowhead-red" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(220, 53, 69, 0.9)" />
      </marker>
      <marker id="arrowhead-green" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(25, 135, 84, 0.9)" />
      </marker>
      <marker id="arrowhead-orange" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(253, 126, 20, 0.9)" />
      </marker>
    </defs>
  `;

  for (const arrow of arrows) {
    const from = getSquareCenter(arrow.from, boardEl, orientation);
    const to = getSquareCenter(arrow.to, boardEl, orientation);

    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const shortenBy = 8;
    const toX = to.x - (dx / len) * shortenBy;
    const toY = to.y - (dy / len) * shortenBy;
    const fromX = from.x + (dx / len) * (shortenBy / 2);
    const fromY = from.y + (dy / len) * (shortenBy / 2);

    const color = arrow.color || 'green';
    const strokeColor = color === 'red' ? 'rgba(220, 53, 69, 0.9)' :
                        color === 'orange' ? 'rgba(253, 126, 20, 0.9)' :
                        'rgba(25, 135, 84, 0.9)';
    const markerId = `arrowhead-${color}`;

    svg += `<line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}"
             stroke="${strokeColor}" stroke-width="8" stroke-linecap="round"
             marker-end="url(#${markerId})" opacity="0.85" />`;
  }

  svg += '</svg>';
  return svg;
}

export function drawArrows(puzzle, game, bestRevealed, showArrows, boardEl, arrowOverlay) {
  if (!showArrows || !puzzle) {
    arrowOverlay.innerHTML = '';
    return;
  }

  const orientation = puzzle.player_color === 'black' ? 'black' : 'white';
  const arrows = [];

  const atOriginalPosition = game.fen() === puzzle.fen;

  if (atOriginalPosition) {
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push({
        from: puzzle.blunder_uci.slice(0, 2),
        to: puzzle.blunder_uci.slice(2, 4),
        color: 'red'
      });
    }

    if (bestRevealed && puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push({
        from: puzzle.best_move_uci.slice(0, 2),
        to: puzzle.best_move_uci.slice(2, 4),
        color: 'green'
      });
    }
  }

  if (arrows.length > 0) {
    arrowOverlay.innerHTML = createArrowSVG(arrows, boardEl, orientation);
  } else {
    arrowOverlay.innerHTML = '';
  }
}

export function clearArrows(arrowOverlay) {
  arrowOverlay.innerHTML = '';
}
