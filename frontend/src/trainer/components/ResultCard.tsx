import { useRef, useEffect, useState } from 'preact/hooks';
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
  onLineMoveClick: (ply: number) => void;
  onLineBack: () => void;
  onLineForward: () => void;
  onPunishmentLineMoveClick: (ply: number) => void;
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
  bestRevealed, moveHistory, onPlayBest, onLineMoveClick, onLineBack, onLineForward, onPunishmentLineMoveClick, onNext, onClose: _onClose,
}: ResultCardProps): preact.JSX.Element | null {
  const cardRef = useRef<HTMLDivElement>(null);
  const { handleRef, restorePosition } = useDrag(cardRef);
  const [punishmentLinePly, setPunishmentLinePly] = useState(0);

  useEffect(() => {
    setPunishmentLinePly(0);
  }, [puzzle?.game_id, puzzle?.ply]);

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
  const punishmentLine = puzzle?.punishment_line ?? [];
  const punishmentLineLength = punishmentLine.length;
  const goToPunishmentLinePly = (ply: number): void => {
    const targetPly = Math.max(0, Math.min(ply, punishmentLineLength));
    setPunishmentLinePly(targetPly);
    onPunishmentLineMoveClick(targetPly);
  };

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
                <div
                  class="board-result-line-row"
                  style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}
                >
                  <button
                    type="button"
                    class="board-result-move line-move-button line-move-button-best"
                    id="bestMoveDisplay"
                    onClick={() => { onLineMoveClick(1); }}
                    style={{ border: '0', background: 'transparent', padding: '0', cursor: 'pointer', font: 'inherit' }}
                  >
                    {puzzle.best_move_san}
                  </button>
                  <span class="board-result-line" id="bestLineDisplay">
                    {puzzle.best_line.length > 1
                      ? puzzle.best_line.slice(1).map((move, index) => (
                          <button
                            key={`${move}-${index}`}
                            type="button"
                            class="line-move-button"
                            onClick={() => { onLineMoveClick(index + 2); }}
                            style={{ border: '0', background: 'transparent', padding: '0 0.12rem', cursor: 'pointer', font: 'inherit', color: 'inherit' }}
                          >
                            {move}
                          </button>
                        ))
                      : ''}
                  </span>
                  <span
                    class="board-result-line-nav"
                    style={{ display: 'inline-flex', gap: '0.35rem', marginLeft: '0.35rem' }}
                  >
                    <button
                      type="button"
                      class="line-nav-button line-nav-button-back"
                      aria-label="Previous move in engine line"
                      title="Previous move"
                      onClick={onLineBack}
                      style={{ minWidth: '2.25rem', padding: '0.15rem 0.45rem', cursor: 'pointer' }}
                    >
                      ◀
                    </button>
                    <button
                      type="button"
                      class="line-nav-button line-nav-button-forward"
                      aria-label="Next move in engine line"
                      title="Next move"
                      onClick={onLineForward}
                      style={{ minWidth: '2.25rem', padding: '0.15rem 0.45rem', cursor: 'pointer' }}
                    >
                      ▶
                    </button>
                  </span>
                </div>
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

              {puzzle.deep_explanation && (
                <details class="board-result-details" id="deepExplanationDetails" open>
                  <summary>Detailed explanation ▸</summary>
                  <div class="board-result-details-body">
                    <div id="deepExplanationText">{puzzle.deep_explanation}</div>
                    {punishmentLine.length > 0 && (
                      <div class="board-result-details-text" id="punishmentLineDisplay">
                        <div
                          class="board-result-line-row"
                          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.4rem' }}
                        >
                          <span>Line:</span>
                          <span class="board-result-line">
                            {punishmentLine.map((move, index) => (
                              <button
                                key={`${move}-${index}`}
                                type="button"
                                class="line-move-button"
                                onClick={() => { goToPunishmentLinePly(index + 1); }}
                                style={{ border: '0', background: 'transparent', padding: '0 0.12rem', cursor: 'pointer', font: 'inherit', color: 'inherit' }}
                              >
                                {move}
                              </button>
                            ))}
                          </span>
                          <span
                            class="board-result-line-nav"
                            style={{ display: 'inline-flex', gap: '0.35rem', marginLeft: '0.35rem' }}
                          >
                            <button
                              type="button"
                              class="line-nav-button line-nav-button-back"
                              aria-label="Previous move in punishment line"
                              title="Previous punishment move"
                              onClick={() => { goToPunishmentLinePly(punishmentLinePly - 1); }}
                              style={{ minWidth: '2.25rem', padding: '0.15rem 0.45rem', cursor: 'pointer' }}
                            >
                              ◀
                            </button>
                            <button
                              type="button"
                              class="line-nav-button line-nav-button-forward"
                              aria-label="Next move in punishment line"
                              title="Next punishment move"
                              onClick={() => { goToPunishmentLinePly(punishmentLinePly + 1); }}
                              style={{ minWidth: '2.25rem', padding: '0.15rem 0.45rem', cursor: 'pointer' }}
                            >
                              ▶
                            </button>
                          </span>
                        </div>
                      </div>
                    )}
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
