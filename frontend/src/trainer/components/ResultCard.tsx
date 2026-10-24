import { useRef, useEffect } from 'preact/hooks';
import { useDrag } from '../hooks/useDrag';
import { Button } from '../../components/primitives/Button';
import type { PuzzleData, FeedbackType } from '../context';

interface ResultCardProps {
  visible: boolean;
  feedbackType: FeedbackType;
  feedbackTitle: string;
  feedbackDetail: string;
  puzzle: PuzzleData | null;
  bestRevealed: boolean;
  moveHistory: string[];
  srsSuspended?: boolean;
  onPlayBest: () => void;
  onPlayRefutation: () => void;
  onNext: () => void;
  onClose: () => void;
}

const ACCENT_MAP: Record<string, string> = {
  correct: 'accent-correct',
  blunder: 'accent-blunder',
  good: 'accent-correct',
  'not-quite': 'accent-revealed',
};

export function ResultCard({
  visible, feedbackType, feedbackTitle, feedbackDetail, puzzle,
  bestRevealed, moveHistory, srsSuspended, onPlayBest, onPlayRefutation, onNext, onClose: _onClose,
}: ResultCardProps): preact.JSX.Element | null {
  const cardRef = useRef<HTMLDivElement>(null);
  const { handleRef, restorePosition } = useDrag(cardRef);

  useEffect(() => {
    if (visible) {
      requestAnimationFrame(() => { restorePosition(); });
    } else if (cardRef.current) {
      cardRef.current.style.left = '';
      cardRef.current.style.top = '';
      cardRef.current.style.right = '';
      cardRef.current.style.bottom = '';
    }
  }, [visible, restorePosition]);

  if (!visible) return null;

  const accentClass = feedbackType ? ACCENT_MAP[feedbackType] ?? 'accent-revealed' : 'accent-revealed';

  return (
    <div
      ref={cardRef}
      id="boardResultCard"
      class={`board-result-card visible ${accentClass} ${bestRevealed ? 'best-revealed' : ''}`}
    >
      <div class="board-result-inner">
        <div ref={handleRef} class="board-result-drag-handle" id="boardResultDragHandle">
          <div class="board-result-drag-handle-bar" />
        </div>
        <div class="board-result-header" id="boardResultHeader">
          <div class="board-result-title" id="feedbackTitle">{feedbackTitle}</div>
          <div class="board-result-detail" id="feedbackDetail">{feedbackDetail}</div>
        </div>
        <div class="board-result-body">
          {puzzle && bestRevealed && (
            <>
              <div class="board-result-best">
                <span class="board-result-move" id="bestMoveDisplay">{puzzle.best_move_san}</span>
                <span class="board-result-line" id="bestLineDisplay">
                  {puzzle.best_line.length > 1 ? puzzle.best_line.slice(1).join(' ') : ''}
                </span>
              </div>

              <div class="board-result-action">
                {/* eslint-disable-next-line no-restricted-syntax -- btn-success has no <Button> variant; keep until a success variant exists */}
                <button class="btn btn-success" id="tryBestBtn" onClick={onPlayBest}>
                  {feedbackType === 'correct' ? t('trainer.button.play_line') : t('trainer.button.play_best')}<kbd>P</kbd>
                </button>
              </div>

              {(puzzle.refutation_line.length > 0 || puzzle.explanation_blunder) && (
                <section class="board-result-section" data-testid="result-blunder">
                  <h3 class="board-result-section-heading">
                    {t('trainer.result.you_played', { move: puzzle.blunder_san })}
                    <span class="board-result-loss">
                      {puzzle.eval_before_display} → {puzzle.eval_after_display}
                    </span>
                  </h3>
                  {puzzle.refutation_line.length > 0 && (
                    <div class="board-result-refutation">
                      <span class="board-result-line" data-testid="refutation-line">
                        {puzzle.refutation_line.join(' ')}
                      </span>
                      <Button variant="secondary" size="sm" testId="show-refutation" onClick={onPlayRefutation}>
                        {t('trainer.button.show_refutation')}
                      </Button>
                    </div>
                  )}
                  {puzzle.explanation_blunder && (
                    <p class="board-result-section-text" id="explanationBlunder">{puzzle.explanation_blunder}</p>
                  )}
                </section>
              )}

              {puzzle.explanation_best && (
                <section class="board-result-section" data-testid="result-best">
                  <h3 class="board-result-section-heading">
                    {t('trainer.result.why_better', { move: puzzle.best_move_san })}
                  </h3>
                  <p class="board-result-section-text" id="explanationBest">{puzzle.explanation_best}</p>
                </section>
              )}

              {puzzle.tactical_pattern && puzzle.tactical_pattern !== 'None' && puzzle.tactical_reason && (
                <details class="board-result-details" id="tacticalDetails">
                  <summary>{t('trainer.details.tactical')} ▸</summary>
                  <div class="board-result-details-body">
                    <div class="board-result-details-heading" id="tacticalInfoTitle">{puzzle.tactical_pattern}</div>
                    <div class="board-result-details-text" id="tacticalInfoReason">{puzzle.tactical_reason}</div>
                  </div>
                </details>
              )}
            </>
          )}

          {srsSuspended && puzzle && (
            <div class="board-result-leech" data-testid="srs-leech-hint">
              <a href={`/game/${encodeURIComponent(puzzle.game_id)}`}>
                {t('trainer.srs.leech_hint')}
              </a>
            </div>
          )}

          {moveHistory.length > 0 && (
            <div class="move-history-section">
              <div class="move-history">{moveHistory.join(' ')}</div>
            </div>
          )}
        </div>
        <div class="board-result-next">
          {/* eslint-disable-next-line no-restricted-syntax -- needs the .board-result-next-btn width:100% hook on the button itself; <Button> takes no className */}
          <button class="btn btn-primary board-result-next-btn" id="overlayNextBtn" onClick={onNext}>
            {t('trainer.shortcuts.next')}<kbd>N</kbd>
          </button>
        </div>
      </div>
    </div>
  );
}
