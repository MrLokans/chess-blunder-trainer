import type { EngineLine } from '../shared/engine/uci';

interface EngineLinesPanelProps {
  fen: string;
  lines: EngineLine[];
  depth: number;
  onPlayLine: (uciMoves: string[]) => void;
}

function formatEval(line: EngineLine): string {
  if (line.mate !== null) return '#' + String(line.mate);
  const cp = line.scoreCp ?? 0;
  const pawns = cp / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
}

function pvToSan(fen: string, pv: string[]): string {
  const game = new Chess(fen);
  const out: string[] = [];
  for (const uci of pv) {
    const move = game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4) || 'q' });
    if (!move) break;
    out.push(move.san);
  }
  return out.join(' ');
}

export function EngineLinesPanel({ fen, lines, depth, onPlayLine }: EngineLinesPanelProps) {
  return (
    <div class="engine-lines" id="engineLines">
      <div class="engine-lines-header">{t('game_review.engine.depth', { depth })}</div>
      {lines.map(line => (
        <button
          key={line.multipv}
          type="button"
          class="engine-line-row"
          onClick={() => { onPlayLine(line.pv); }}
        >
          <span class="engine-line-eval">{formatEval(line)}</span>
          <span class="engine-line-pv">{pvToSan(fen, line.pv)}</span>
        </button>
      ))}
    </div>
  );
}
