import type { HighlightMap } from './highlights';

export interface ChessgroundShape {
  orig: string;
  dest?: string;
  brush?: string;
}

// Minimal slice of the Chessground API needed to apply visual overlays.
export interface ChessgroundVisualApi {
  set(config: Record<string, unknown>): void;
  setAutoShapes(shapes: ChessgroundShape[]): void;
}

export interface BoardArrow {
  from: string;
  to: string;
  color: string;
}

// Arrow colours map to *registered* Chessground brush keys. Square highlights do
// NOT go through brushes — see applyBoardVisuals.
const ARROW_BRUSH: Record<string, string> = {
  red: 'red',
  orange: 'yellow',
  green: 'green',
};

export function arrowBrush(color: string): string {
  return ARROW_BRUSH[color] ?? 'green';
}

export function arrowsToShapes(arrows: BoardArrow[]): ChessgroundShape[] {
  return arrows.map(a => ({ orig: a.from, dest: a.to, brush: arrowBrush(a.color) }));
}

/**
 * Apply square highlights and arrows to a Chessground instance.
 *
 * Square highlights are CSS class names (e.g. `highlight-hanging`) styled by
 * `chessground-theme.css` via `cg-board square.<class>`. Chessground only attaches
 * those classes to <square> elements through its `highlight.custom` map — NOT through
 * autoShape brushes (an autoShape brush must be a key in `drawable.brushes`, which these
 * class names are not, so they render nothing). Arrows, by contrast, are real autoShapes
 * keyed by registered brushes. Keeping both paths in one helper is the single source of
 * truth that previously diverged between the trainer and game-review boards.
 */
export function applyBoardVisuals(
  cg: ChessgroundVisualApi,
  highlights: HighlightMap,
  arrows: BoardArrow[],
): void {
  cg.set({
    highlight: {
      lastMove: true,
      check: true,
      custom: highlights.size > 0 ? highlights : undefined,
    },
  });
  cg.setAutoShapes(arrowsToShapes(arrows));
}

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
