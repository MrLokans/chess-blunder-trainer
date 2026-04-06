export function updateEvalBar(
  cp: number,
  playerColor: string,
  fillEl: HTMLElement,
  valueEl: HTMLElement,
): void {
  const playerCp = playerColor === 'black' ? -cp : cp;

  const maxCp = 500;
  const normalized = Math.max(-maxCp, Math.min(maxCp, playerCp));
  const percentage = 50 + (normalized / maxCp) * 50;

  fillEl.style.height = percentage + '%';

  let displayVal: string;
  if (Math.abs(cp) >= 10000) {
    displayVal = cp > 0 ? '+M' : '-M';
  } else {
    displayVal = (cp >= 0 ? '+' : '') + (cp / 100).toFixed(1);
  }
  valueEl.textContent = displayVal;
  valueEl.className = 'eval-value ' + (playerCp >= 0 ? 'positive' : 'negative');
}
