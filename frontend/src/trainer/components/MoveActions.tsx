interface MoveActionsProps {
  hasPuzzle: boolean;
  bestRevealed: boolean;
  onReset: () => void;
  onReveal: () => void;
  onNext: () => void;
  onUndo: () => void;
}

export function MoveActions({
  hasPuzzle, bestRevealed,
  onReset, onReveal, onNext, onUndo: _onUndo,
}: MoveActionsProps): preact.JSX.Element | null {
  if (!hasPuzzle) return null;

  return (
    <div class="action-keys">
      <button class="action-key" id="resetBtn" onClick={onReset} aria-label={t('trainer.shortcuts.reset')} title={t('trainer.shortcuts.reset')}>
        <kbd>R</kbd>
      </button>

      {!bestRevealed && (
        <button class="action-key" id="showBestBtn" onClick={onReveal} aria-label={t('trainer.shortcuts.show_best')} title={t('trainer.shortcuts.show_best')}>
          <kbd>B</kbd>
        </button>
      )}

      <button class="action-key" id="nextBtn" onClick={onNext} aria-label={t('trainer.shortcuts.next')} title={t('trainer.shortcuts.next')}>
        <kbd>N</kbd>
      </button>
    </div>
  );
}
