import { useMemo } from 'preact/hooks';
import type { EngineLine } from '../shared/engine/uci';

interface EngineLinesPanelProps {
  fen: string;
  lines: EngineLine[];
  depth: number;
  onPlayLine: (uciMoves: string[]) => void;
}

// The PV row is a single ellipsised line, so replaying the full (often 20+ move)
// PV through chess.js just to truncate it is wasted work on every engine tick.
const PV_PREVIEW_PLIES = 8;

function formatEval(line: EngineLine): string {
  if (line.mate !== null) return '#' + String(line.mate);
  const cp = line.scoreCp ?? 0;
  const pawns = cp / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
}

function pvToSan(fen: string, pv: string[]): string {
  const game = new Chess(fen);
  const out: string[] = [];
  for (const uci of pv.slice(0, PV_PREVIEW_PLIES)) {
    const move = game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4) || 'q' });
    if (!move) break;
    out.push(move.san);
  }
  return out.join(' ');
}

export function EngineLinesPanel({ fen, lines, depth, onPlayLine }: EngineLinesPanelProps) {
  const sans = useMemo(() => lines.map(line => pvToSan(fen, line.pv)), [fen, lines]);

  return (
    <div class="engine-lines" id="engineLines">
      <div class="engine-lines-header">{t('game_review.engine.depth', { depth })}</div>
      {lines.map((line, i) => (
        <button
          key={line.multipv}
          type="button"
          class="engine-line-row"
          onClick={() => { onPlayLine(line.pv); }}
        >
          <span class="engine-line-eval">{formatEval(line)}</span>
          <span class="engine-line-pv">{sans[i]}</span>
        </button>
      ))}
    </div>
  );
}
