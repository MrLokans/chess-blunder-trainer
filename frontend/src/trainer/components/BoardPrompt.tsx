interface BoardPromptProps {
  submitted: boolean;
  bestRevealed: boolean;
  submitting: boolean;
  hasPuzzle: boolean;
}

export function BoardPrompt({ submitted, bestRevealed, submitting, hasPuzzle }: BoardPromptProps): preact.JSX.Element | null {
  if (!hasPuzzle || bestRevealed) return null;

  if (submitting) {
    return (
      <div class="board-prompt" id="movePrompt">
        <div class="submit-spinner">
          <span class="inline-spinner" /> {t('trainer.feedback.evaluating')}
        </div>
      </div>
    );
  }

  return (
    <div class="board-prompt" id="movePrompt">
      <div class="section-title">{!submitted && t('trainer.prompt.make_better')}</div>
    </div>
  );
}
