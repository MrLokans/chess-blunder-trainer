import { Chessground } from '@vendor/chessground';
import { buildBoardSvgDataUrl } from './board-theme';

interface ChessgroundShape { orig: string; dest?: string; brush?: string; }

interface ChessgroundApi {
  set(config: Record<string, unknown>): void;
  setAutoShapes(shapes: ChessgroundShape[]): void;
  destroy(): void;
}

export type MoveHandler = (orig: string, dest: string, promotion: string) => void;

export function buildDests(game: ChessInstance): Map<string, string[]> {
  const dests = new Map<string, string[]>();
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = (files[f] ?? '') + String(r);
      const moves = game.moves({ square: sq, verbose: true });
      if (moves.length > 0) dests.set(sq, moves.map(m => m.to));
    }
  }
  return dests;
}

export class AnalysisBoard {
  private _el: HTMLElement;
  private _cg: ChessgroundApi | null = null;
  private _gameRef: () => ChessInstance;
  private _onMove: MoveHandler;
  private _observer: MutationObserver | null = null;
  private _boardBgUrl = '';

  constructor(
    containerEl: HTMLElement,
    opts: { orientation?: string; gameRef: () => ChessInstance; onMove: MoveHandler },
  ) {
    this._el = containerEl;
    this._gameRef = opts.gameRef;
    this._onMove = opts.onMove;
    const game = this._gameRef();
    this._cg = Chessground(this._el, {
      fen: game.fen(),
      orientation: opts.orientation ?? 'white',
      coordinates: true,
      ranksPosition: 'left',
      animation: { enabled: true, duration: 150 },
      movable: {
        free: false,
        color: 'both',
        dests: buildDests(game),
        showDests: true,
        events: { after: (orig: string, dest: string) => { this._afterMove(orig, dest); } },
      },
      draggable: { enabled: true, showGhost: true },
      highlight: { lastMove: true, check: true },
      premovable: { enabled: false },
      // User free-draw disabled; engine arrows use setShapes -> setAutoShapes, which is unaffected.
      drawable: { enabled: false },
    });
    this._applyBoardBackground();
    this._observer = new MutationObserver(() => { this._setBoardInline(); });
    this._observer.observe(this._el, { childList: true });
  }

  private _afterMove(orig: string, dest: string): void {
    const cg = this._cg;
    if (!cg) return;
    const game = this._gameRef();
    const move = game.move({ from: orig, to: dest, promotion: 'q' });
    if (!move) { cg.set({ fen: game.fen() }); return; }
    const turn = game.turn() === 'w' ? 'white' : 'black';
    cg.set({
      fen: game.fen(),
      turnColor: turn,
      lastMove: [orig, dest],
      movable: { color: 'both', dests: buildDests(game) },
    });
    this._onMove(orig, dest, move.promotion ?? '');
  }

  setPosition(game: ChessInstance, lastMove: [string, string] | null): void {
    this._cg?.set({
      fen: game.fen(),
      turnColor: game.turn() === 'w' ? 'white' : 'black',
      lastMove: lastMove ?? undefined,
      movable: { color: 'both', dests: buildDests(game) },
    });
  }

  setOrientation(color: string): void { this._cg?.set({ orientation: color }); }

  setShapes(shapes: ChessgroundShape[]): void { this._cg?.setAutoShapes(shapes); }

  private _applyBoardBackground(): void {
    const style = getComputedStyle(document.documentElement);
    const light = style.getPropertyValue('--board-light').trim() || '#E0E0E0';
    const dark = style.getPropertyValue('--board-dark').trim() || '#A0A0A0';
    this._boardBgUrl = `url("${buildBoardSvgDataUrl(light, dark)}")`;
    this._el.style.setProperty('--board-bg', this._boardBgUrl);
    this._setBoardInline();
  }

  private _setBoardInline(): void {
    const board = this._el.querySelector('cg-board');
    if (board instanceof HTMLElement) board.style.backgroundImage = this._boardBgUrl;
  }

  destroy(): void {
    this._observer?.disconnect();
    this._cg?.destroy();
    this._cg = null;
    this._observer = null;
  }
}
