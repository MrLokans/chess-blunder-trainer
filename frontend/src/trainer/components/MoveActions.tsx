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
  onShowShortcuts: () => void;
}

export function MoveActions({
  hasPuzzle, submitted, bestRevealed, submitting, hasMove,
  onSubmit, onReset, onReveal, onNext, onUndo: _onUndo, onShowShortcuts,
}: MoveActionsProps): preact.JSX.Element | null {
  if (!hasPuzzle) return null;

  return (
    <div class="panel-section">
      <div class="action-keys">
        {!submitted && !bestRevealed && hasMove && (
          <button class={`action-key ${submitting ? 'submitting' : ''}`} id="submitBtn" onClick={onSubmit} disabled={submitting}>
            <kbd>Enter</kbd><span class="action-label">{t('trainer.shortcuts.submit')}</span>
          </button>
        )}

        <button class="action-key" id="resetBtn" onClick={onReset}>
          <kbd>R</kbd><span class="action-label">{t('trainer.shortcuts.reset')}</span>
        </button>

        {!bestRevealed && (
          <button class="action-key" id="showBestBtn" onClick={onReveal} disabled={submitting}>
            <kbd>B</kbd><span class="action-label">{t('trainer.shortcuts.show_best')}</span>
          </button>
        )}

        <button class="action-key" id="nextBtn" onClick={onNext}>
          <kbd>N</kbd><span class="action-label">{t('trainer.shortcuts.next')}</span>
        </button>

        <button class="action-key action-key-muted" id="shortcutsHintBtn" onClick={onShowShortcuts} title="Keyboard shortcuts (?)">
          <kbd>?</kbd><span class="action-label">{t('trainer.shortcuts.title')}</span>
        </button>
      </div>
    </div>
  );
}
