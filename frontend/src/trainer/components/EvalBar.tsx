import { MAX_EVAL_CP } from '../../shared/eval-bar';

interface EvalBarProps {
  // From the player's perspective (puzzle evals are stored mover-POV).
  cp: number;
}

export function EvalBar({ cp }: EvalBarProps): preact.JSX.Element {
  const maxCp = MAX_EVAL_CP;
  const normalized = Math.max(-maxCp, Math.min(maxCp, cp));
  const fillPercent = 50 + (normalized / maxCp) * 50;

  let display: string;
  if (Math.abs(cp) >= 10000) {
    display = cp > 0 ? '+M' : '-M';
  } else {
    const pawns = cp / 100;
    display = (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
  }

  return (
    <div class="eval-bar-container">
      <div class="eval-value" id="evalValue">{display}</div>
      <div class="eval-bar" id="evalBar">
        <div class="eval-bar-fill" id="evalBarFill" style={{ height: `${String(fillPercent)}%` }} />
      </div>
    </div>
  );
}
