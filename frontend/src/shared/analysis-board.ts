import { Chessground } from '@vendor/chessground';
import { applyBoardVisuals, buildDests, type BoardArrow, type ChessgroundVisualApi } from './board-visuals';
import type { HighlightMap } from './highlights';

interface ChessgroundApi extends ChessgroundVisualApi {
  destroy(): void;
}

export type MoveHandler = (orig: string, dest: string, promotion: string) => void;

// Re-exported for callers that build move destinations off the analysis board.
export { buildDests };

export class AnalysisBoard {
  private _el: HTMLElement;
  private _cg: ChessgroundApi | null = null;
  private _gameRef: () => ChessInstance;
  private _onMove: MoveHandler;

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

  // Square highlights go through Chessground's highlight.custom map (CSS classes);
  // arrows go through autoShapes with registered brushes. See applyBoardVisuals.
  setVisuals(highlights: HighlightMap, arrows: BoardArrow[]): void {
    if (this._cg) applyBoardVisuals(this._cg, highlights, arrows);
  }

  destroy(): void {
    this._cg?.destroy();
    this._cg = null;
  }
}
