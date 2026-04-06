interface ChessgroundShape {
  orig: string;
  dest?: string;
  brush?: string;
}

interface ChessgroundApi {
  set(config: Record<string, unknown>): void;
  setAutoShapes(shapes: ChessgroundShape[]): void;
  destroy(): void;
}

interface Arrow {
  from: string;
  to: string;
  color: string;
}

interface BoardAdapterOptions {
  fen: string;
  orientation: string;
  game: ChessInstance;
  onMove?: (orig: string, dest: string, move: { san: string; from: string; to: string; promotion?: string }) => void;
  coordinates?: boolean;
  interactive?: boolean;
}

import { Chessground } from '@vendor/chessground';

function buildDests(game: ChessInstance): Map<string, string[]> {
  const dests = new Map<string, string[]>();
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f]! + r;
      const moves = game.moves({ square: sq, verbose: true });
      if (moves.length > 0) {
        dests.set(sq, moves.map(m => m.to));
      }
    }
  }
  return dests;
}

export class BoardAdapter {
  private _elementId: string;
  private _orientation: string;
  private _game: ChessInstance;
  private _onMove?: BoardAdapterOptions['onMove'];
  private _shapes: ChessgroundShape[] = [];
  private _highlightShapes: ChessgroundShape[] = [];
  private _el: HTMLElement;
  private _cg: ChessgroundApi | null;
  private _preMoveTimer1: ReturnType<typeof setTimeout> | null = null;
  private _preMoveTimer2: ReturnType<typeof setTimeout> | null = null;

  constructor(elementId: string, options: BoardAdapterOptions) {
    this._elementId = elementId;
    this._orientation = options.orientation;
    this._game = options.game;
    this._onMove = options.onMove;
    this._el = document.getElementById(elementId)!;
    this._el.innerHTML = '';

    this.setCoordinates(options.coordinates ?? false);

    const cgColor = options.orientation === 'black' ? 'black' : 'white';
    const turnColor = options.fen.split(' ')[1] === 'w' ? 'white' : 'black';
    const interactive = options.interactive ?? true;

    this._cg = Chessground(this._el, {
      fen: options.fen,
      orientation: cgColor,
      turnColor,
      coordinates: true,
      ranksPosition: 'left',
      animation: { enabled: true, duration: 150 },
      movable: {
        free: false,
        color: interactive ? cgColor : undefined,
        dests: interactive ? buildDests(options.game) : new Map(),
        showDests: true,
        events: {
          after: (orig: string, dest: string) => this._handleMove(orig, dest),
        },
      },
      draggable: { enabled: true, showGhost: true },
      highlight: { lastMove: true, check: true },
      premovable: { enabled: false },
      drawable: { enabled: false },
    });
  }

  private _handleMove(orig: string, dest: string): void {
    const move = this._game.move({ from: orig, to: dest, promotion: 'q' });
    if (!move) return;

    const turnColor = this._game.turn() === 'w' ? 'white' : 'black';
    this._cg!.set({
      fen: this._game.fen(),
      turnColor,
      movable: {
        color: this._orientation === 'black' ? 'black' : 'white',
        dests: buildDests(this._game),
      },
      lastMove: [orig, dest],
    });

    if (this._onMove) {
      this._onMove(orig, dest, move);
    }
  }

  setPosition(fen: string, game: ChessInstance): void {
    this._game = game;
    const turnColor = game.turn() === 'w' ? 'white' : 'black';
    this._cg!.set({
      fen,
      turnColor,
      lastMove: undefined,
      movable: {
        color: this._orientation === 'black' ? 'black' : 'white',
        dests: buildDests(game),
      },
    });
    this._shapes = [];
    this._highlightShapes = [];
    this._cg!.setAutoShapes([]);
  }

  animatePreMove(
    puzzleFen: string,
    from: string,
    to: string,
    game: ChessInstance,
    callback?: () => void,
  ): void {
    this._game = game;
    this._clearPreMoveTimers();

    this._preMoveTimer1 = setTimeout(() => {
      if (!this._cg) return;
      this._cg.set({
        animation: { duration: 350 },
        fen: puzzleFen,
        lastMove: [from, to],
        turnColor: game.turn() === 'w' ? 'white' : 'black',
      });

      this._preMoveTimer2 = setTimeout(() => {
        if (!this._cg) return;
        this._cg.set({
          animation: { duration: 150 },
          movable: {
            color: this._orientation === 'black' ? 'black' : 'white',
            dests: buildDests(game),
          },
        });
        if (callback) callback();
      }, 400);
    }, 400);
  }

  private _clearPreMoveTimers(): void {
    if (this._preMoveTimer1) { clearTimeout(this._preMoveTimer1); this._preMoveTimer1 = null; }
    if (this._preMoveTimer2) { clearTimeout(this._preMoveTimer2); this._preMoveTimer2 = null; }
  }

  setOrientation(color: string): void {
    this._orientation = color;
    this._cg!.set({ orientation: color });
  }

  setCoordinates(enabled: boolean): void {
    this._el.classList.toggle('hide-coords', !enabled);
  }

  drawArrows(arrows: Arrow[]): void {
    this._shapes = arrows.map(a => ({
      orig: a.from,
      dest: a.to,
      brush: a.color === 'red' ? 'red' : a.color === 'orange' ? 'yellow' : 'green',
    }));
    this._updateAutoShapes();
  }

  clearArrows(): void {
    this._shapes = [];
    this._updateAutoShapes();
  }

  highlightSquares(highlights: Map<string, string>): void {
    this._highlightShapes = [];
    for (const [square, brush] of highlights) {
      this._highlightShapes.push({ orig: square, brush });
    }
    this._updateAutoShapes();
  }

  clearHighlights(): void {
    this._highlightShapes = [];
    this._updateAutoShapes();
  }

  setCustomHighlight(customMap: Map<string, string> | undefined): void {
    this._cg!.set({ highlight: { lastMove: true, check: true, custom: customMap } });
  }

  clearCustomHighlight(): void {
    this._cg!.set({ highlight: { lastMove: true, check: true, custom: undefined } });
  }

  private _updateAutoShapes(): void {
    this._cg!.setAutoShapes([...this._shapes, ...this._highlightShapes]);
  }

  updateMovable(game: ChessInstance): void {
    this._game = game;
    const turnColor = game.turn() === 'w' ? 'white' : 'black';
    this._cg!.set({
      turnColor,
      movable: { dests: buildDests(game) },
    });
  }

  destroy(): void {
    this._clearPreMoveTimers();
    if (this._cg) {
      this._cg.destroy();
      this._cg = null;
    }
  }
}
