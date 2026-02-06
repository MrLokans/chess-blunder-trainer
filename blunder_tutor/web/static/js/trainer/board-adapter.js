import { Chessground } from '../../vendor/chessground-9.1.1.min.js';

function buildDests(game) {
  const dests = new Map();
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const moves = game.moves({ square: sq, verbose: true });
      if (moves.length > 0) {
        dests.set(sq, moves.map(m => m.to));
      }
    }
  }
  return dests;
}

export class BoardAdapter {
  constructor(elementId, { fen, orientation, game, onMove }) {
    this._elementId = elementId;
    this._orientation = orientation;
    this._game = game;
    this._onMove = onMove;
    this._shapes = [];
    this._highlightShapes = [];
    this._el = document.getElementById(elementId);
    this._el.innerHTML = '';

    const cgColor = orientation === 'black' ? 'black' : 'white';
    const turnColor = game.turn() === 'w' ? 'white' : 'black';

    this._cg = Chessground(this._el, {
      fen: fen,
      orientation: cgColor,
      turnColor: turnColor,
      coordinates: true,
      animation: { enabled: true, duration: 150 },
      movable: {
        free: false,
        color: cgColor,
        dests: buildDests(game),
        showDests: true,
        events: {
          after: (orig, dest) => this._handleMove(orig, dest)
        }
      },
      draggable: { enabled: true, showGhost: true },
      highlight: { lastMove: true, check: true },
      premovable: { enabled: false },
      drawable: { enabled: false }
    });
  }

  _handleMove(orig, dest) {
    const move = this._game.move({ from: orig, to: dest, promotion: 'q' });
    if (!move) return;

    const turnColor = this._game.turn() === 'w' ? 'white' : 'black';
    this._cg.set({
      fen: this._game.fen(),
      turnColor: turnColor,
      movable: {
        color: this._orientation === 'black' ? 'black' : 'white',
        dests: buildDests(this._game)
      },
      lastMove: [orig, dest]
    });

    if (this._onMove) {
      this._onMove(orig, dest, move);
    }
  }

  setPosition(fen, game) {
    this._game = game;
    const turnColor = game.turn() === 'w' ? 'white' : 'black';
    this._cg.set({
      fen: fen,
      turnColor: turnColor,
      lastMove: undefined,
      movable: {
        color: this._orientation === 'black' ? 'black' : 'white',
        dests: buildDests(game)
      }
    });
    this._shapes = [];
    this._highlightShapes = [];
    this._cg.setAutoShapes([]);
  }

  setOrientation(color) {
    this._orientation = color;
    this._cg.set({ orientation: color });
  }

  drawArrows(arrows) {
    this._shapes = arrows.map(a => ({
      orig: a.from,
      dest: a.to,
      brush: a.color === 'red' ? 'red' : a.color === 'orange' ? 'yellow' : 'green'
    }));
    this._updateAutoShapes();
  }

  clearArrows() {
    this._shapes = [];
    this._updateAutoShapes();
  }

  highlightSquares(highlights) {
    this._highlightShapes = [];
    for (const [square, brush] of highlights) {
      this._highlightShapes.push({
        orig: square,
        brush: brush
      });
    }
    this._updateAutoShapes();
  }

  clearHighlights() {
    this._highlightShapes = [];
    this._updateAutoShapes();
  }

  setCustomHighlight(customMap) {
    this._cg.set({ highlight: { lastMove: true, check: true, custom: customMap } });
  }

  clearCustomHighlight() {
    this._cg.set({ highlight: { lastMove: true, check: true, custom: undefined } });
  }

  _updateAutoShapes() {
    this._cg.setAutoShapes([...this._shapes, ...this._highlightShapes]);
  }

  updateMovable(game) {
    this._game = game;
    const turnColor = game.turn() === 'w' ? 'white' : 'black';
    this._cg.set({
      turnColor: turnColor,
      movable: {
        dests: buildDests(game)
      }
    });
  }

  destroy() {
    if (this._cg) {
      this._cg.destroy();
      this._cg = null;
    }
  }
}
