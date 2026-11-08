import { useEffect, useRef } from 'preact/hooks';
import { Chessground } from '@vendor/chessground';

interface MiniBoardProps {
  fen: string;
  orientation: 'white' | 'black';
  move: string;
  brush: 'green' | 'red';
  label: string;
}

export function MiniBoard({ fen, orientation, move, brush, label }: MiniBoardProps): preact.JSX.Element {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const from = move.slice(0, 2);
    const to = move.slice(2, 4);
    const cg = Chessground(el, {
      fen,
      orientation,
      viewOnly: true,
      coordinates: false,
      animation: { enabled: false },
      lastMove: [from, to],
      drawable: { enabled: false, visible: true, autoShapes: [{ orig: from, dest: to, brush }] },
    });
    // Chessground sizes itself once at mount; the panel column can still settle after that.
    const observer = new ResizeObserver(() => { cg.redrawAll(); });
    observer.observe(el);
    return () => {
      observer.disconnect();
      cg.destroy();
    };
  }, [fen, orientation, move, brush]);

  return (
    <div class="mini-board" role="img" aria-label={label}>
      <div ref={ref} class="cg-wrap" />
    </div>
  );
}
