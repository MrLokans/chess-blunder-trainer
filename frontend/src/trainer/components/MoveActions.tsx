import { Button } from '../../components/primitives/Button';

interface MoveActionsProps {
  hasPuzzle: boolean;
  bestRevealed: boolean;
  onReset: () => void;
  onReveal: () => void;
  onNext: () => void;
}

export function MoveActions({
  hasPuzzle, bestRevealed, onReset, onReveal, onNext,
}: MoveActionsProps): preact.JSX.Element | null {
  if (!hasPuzzle) return null;

  return (
    <div class="move-actions">
      <Button variant="secondary" size="sm" testId="reset" onClick={onReset}>
        {t('trainer.shortcuts.reset')}<kbd>R</kbd>
      </Button>
      <Button variant="secondary" size="sm" testId="show-best" disabled={bestRevealed} onClick={onReveal}>
        {t('trainer.shortcuts.show_best')}<kbd>B</kbd>
      </Button>
      <Button variant="secondary" size="sm" testId="next" onClick={onNext}>
        {t('trainer.shortcuts.next')}<kbd>N</kbd>
      </Button>
    </div>
  );
}
