import { useRef, useEffect } from 'preact/hooks';
import { useDrag } from '../hooks/useDrag';
import type { PuzzleData, FeedbackType } from '../context';

interface ResultCardProps {
  visible: boolean;
  feedbackType: FeedbackType;
  feedbackTitle: string;
  feedbackDetail: string;
  puzzle: PuzzleData | null;
  bestRevealed: boolean;
  moveHistory: string[];
  onPlayBest: () => void;
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
  bestRevealed, moveHistory, onPlayBest, onNext, onClose: _onClose,
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
  const showTryBest = feedbackType !== 'correct';

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

              {showTryBest && (
                <div class="board-result-action">
                  <button class="btn btn-success" id="tryBestBtn" onClick={onPlayBest}>
                    {t('trainer.button.play_best')}<kbd>P</kbd>
                  </button>
                </div>
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

              {(puzzle.explanation_blunder || puzzle.explanation_best) && (
                <details class="board-result-details" id="explanationDetails">
                  <summary>{t('trainer.details.explanation')} ▸</summary>
                  <div class="board-result-details-body">
                    <div id="explanationBlunder">{puzzle.explanation_blunder || ''}</div>
                    <div id="explanationBest">{puzzle.explanation_best || ''}</div>
                  </div>
                </details>
              )}
            </>
          )}

          {moveHistory.length > 0 && (
            <div class="move-history-section">
              <div class="move-history">{moveHistory.join(' ')}</div>
            </div>
          )}
        </div>
        <div class="board-result-next">
          <button class="btn btn-primary board-result-next-btn" id="overlayNextBtn" onClick={onNext}>
            {t('trainer.shortcuts.next')}<kbd>N</kbd>
          </button>
        </div>
      </div>
    </div>
  );
}
