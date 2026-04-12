export const MAX_EVAL_CP = 500;

export function updateEvalBar(
  cp: number,
  playerColor: string,
  fillEl: HTMLElement,
  valueEl: HTMLElement,
): void {
  const playerCp = playerColor === 'black' ? -cp : cp;

  const normalized = Math.max(-MAX_EVAL_CP, Math.min(MAX_EVAL_CP, playerCp));
  const percentage = 50 + (normalized / MAX_EVAL_CP) * 50;

  fillEl.style.height = String(percentage) + '%';

  let displayVal: string;
  if (Math.abs(cp) >= 10000) {
    displayVal = cp > 0 ? '+M' : '-M';
  } else {
    displayVal = (cp >= 0 ? '+' : '') + (cp / 100).toFixed(1);
  }
  valueEl.textContent = displayVal;
  valueEl.className = 'eval-value ' + (playerCp >= 0 ? 'positive' : 'negative');
}
