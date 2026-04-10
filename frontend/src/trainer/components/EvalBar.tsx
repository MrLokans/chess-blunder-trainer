interface EvalBarProps {
  cp: number;
  playerColor: string;
}

export function EvalBar({ cp, playerColor }: EvalBarProps): preact.JSX.Element {
  const maxCp = 500;
  const normalized = Math.max(-maxCp, Math.min(maxCp, cp));
  const whitePercent = 50 + (normalized / maxCp) * 50;
  const fillPercent = playerColor === 'white' ? whitePercent : 100 - whitePercent;

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
        <div class="eval-bar-fill" id="evalBarFill" style={{ height: `${fillPercent}%` }} />
      </div>
    </div>
  );
}
