import { useEffect, useRef } from 'preact/hooks';
import { Chessground } from '@vendor/chessground';

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

type HighlightMap = Map<string, string>;

interface Arrow {
  from: string;
  to: string;
  color: string;
}

interface BoardProps {
  fen: string;
  orientation: 'white' | 'black';
  interactive: boolean;
  coordinates: boolean;
  highlights: HighlightMap;
  arrows: Arrow[];
  gameRef: preact.RefObject<ChessInstance | null>;
  onMove: (orig: string, dest: string, move: { san: string; from: string; to: string; promotion?: string }) => void;
  animateFrom?: { fen: string; from: string; to: string; onComplete: () => void } | null;
}

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

export function Board({
  fen, orientation, interactive, coordinates, highlights,
  arrows, gameRef, onMove, animateFrom,
}: BoardProps): preact.JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const cgRef = useRef<ChessgroundApi | null>(null);
  const onMoveRef = useRef(onMove);
  onMoveRef.current = onMove;
  const orientationRef = useRef(orientation);
  orientationRef.current = orientation;
  const interactiveRef = useRef(interactive);
  interactiveRef.current = interactive;

  // Mount Chessground once
  useEffect(() => {
    const el = containerRef.current;
    if (!el || cgRef.current) return;

    el.innerHTML = '';
    const game = gameRef.current;
    const turnColor = game?.turn() === 'w' ? 'white' : 'black';

    const cg = Chessground(el, {
      fen,
      orientation,
      turnColor,
      coordinates: true,
      ranksPosition: 'left',
      animation: { enabled: true, duration: 150 },
      movable: {
        free: false,
        color: interactive ? orientation : undefined,
        dests: game && interactive ? buildDests(game) : new Map(),
        showDests: true,
        events: {
          after: (orig: string, dest: string) => {
            const g = gameRef.current;
            if (!g) return;
            const move = g.move({ from: orig, to: dest, promotion: 'q' });
            if (!move) return;

            const turnCol = g.turn() === 'w' ? 'white' : 'black';
            cg.set({
              fen: g.fen(),
              turnColor: turnCol,
              movable: {
                color: interactiveRef.current ? orientationRef.current : undefined,
                dests: interactiveRef.current ? buildDests(g) : new Map(),
              },
              lastMove: [orig, dest],
            });

            onMoveRef.current(orig, dest, move);
          },
        },
      },
      draggable: { enabled: true, showGhost: true },
      highlight: { lastMove: true, check: true },
      premovable: { enabled: false },
      drawable: { enabled: false },
    });
    cgRef.current = cg;

    return () => {
      cg.destroy();
      cgRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync fen + movable when position changes
  useEffect(() => {
    const cg = cgRef.current;
    if (!cg) return;
    const game = gameRef.current;
    const turnColor = game?.turn() === 'w' ? 'white' : 'black';
    cg.set({
      fen,
      turnColor,
      movable: {
        color: interactive ? orientation : undefined,
        dests: game && interactive ? buildDests(game) : new Map(),
      },
    });
  }, [fen, interactive, orientation, gameRef]);

  // Sync orientation
  useEffect(() => {
    cgRef.current?.set({ orientation });
  }, [orientation]);

  // Sync coordinates
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.classList.toggle('hide-coords', !coordinates);
  }, [coordinates]);

  // Sync highlights + arrows
  useEffect(() => {
    const cg = cgRef.current;
    if (!cg) return;
    const highlightShapes: ChessgroundShape[] = Array.from(highlights.entries()).map(([square, brush]) => ({
      orig: square,
      brush,
    }));
    const arrowShapes: ChessgroundShape[] = arrows.map(a => ({
      orig: a.from,
      dest: a.to,
      brush: a.color === 'red' ? 'red' : a.color === 'orange' ? 'yellow' : 'green',
    }));
    cg.setAutoShapes([...arrowShapes, ...highlightShapes]);
  }, [highlights, arrows]);

  // Pre-move animation
  useEffect(() => {
    if (!animateFrom) return;
    const cg = cgRef.current;
    if (!cg) return;
    const game = gameRef.current;

    const t1 = setTimeout(() => {
      cg.set({
        animation: { duration: 350 },
        fen,
        lastMove: [animateFrom.from, animateFrom.to],
        turnColor: game?.turn() === 'w' ? 'white' : 'black',
      });

      const t2 = setTimeout(() => {
        cg.set({
          animation: { duration: 150 },
          movable: {
            color: orientationRef.current,
            dests: game ? buildDests(game) : new Map(),
          },
        });
        animateFrom.onComplete();
      }, 400);
      return () => clearTimeout(t2);
    }, 400);

    return () => clearTimeout(t1);
  }, [animateFrom, fen, gameRef]);

  return <div ref={containerRef} class="cg-wrap" id="board" />;
}
