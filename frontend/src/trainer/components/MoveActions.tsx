interface MoveActionsProps {
  hasPuzzle: boolean;
  submitted: boolean;
  bestRevealed: boolean;
  submitting: boolean;
  hasMove: boolean;
  onSubmit: () => void;
  onReset: () => void;
  onReveal: () => void;
  onNext: () => void;
  onUndo: () => void;
}

export function MoveActions({
  hasPuzzle, submitted, bestRevealed, submitting, hasMove,
  onSubmit, onReset, onReveal, onNext, onUndo: _onUndo,
}: MoveActionsProps): preact.JSX.Element | null {
  if (!hasPuzzle) return null;

  return (
    <div class="action-keys">
      {!submitted && !bestRevealed && hasMove && (
        <button class={`action-key ${submitting ? 'submitting' : ''}`} id="submitBtn" onClick={onSubmit} disabled={submitting} aria-label={t('trainer.shortcuts.submit')} title={t('trainer.shortcuts.submit')}>
          <kbd>Enter</kbd>
        </button>
      )}

      <button class="action-key" id="resetBtn" onClick={onReset} aria-label={t('trainer.shortcuts.reset')} title={t('trainer.shortcuts.reset')}>
        <kbd>R</kbd>
      </button>

      {!bestRevealed && (
        <button class="action-key" id="showBestBtn" onClick={onReveal} disabled={submitting} aria-label={t('trainer.shortcuts.show_best')} title={t('trainer.shortcuts.show_best')}>
          <kbd>B</kbd>
        </button>
      )}

      <button class="action-key" id="nextBtn" onClick={onNext} aria-label={t('trainer.shortcuts.next')} title={t('trainer.shortcuts.next')}>
        <kbd>N</kbd>
      </button>
    </div>
  );
}
