import { useEffect, useRef } from 'preact/hooks';
import { Button } from '../../components/primitives/Button';
import { scrollBehavior } from '../../shared/motion';
import { MiniBoard } from './MiniBoard';
import type { PuzzleData, FeedbackType } from '../context';

export interface UserAttempt {
  san: string;
  uci: string;
  evalDisplay: string;
}

interface ResultCardProps {
  visible: boolean;
  feedbackType: FeedbackType;
  feedbackTitle: string;
  feedbackDetail: string;
  puzzle: PuzzleData | null;
  bestRevealed: boolean;
  userAttempt: UserAttempt | null;
  moveHistory: string[];
  srsSuspended?: boolean;
  onPlayBest: () => void;
  onPlayRefutation: () => void;
  onNext: () => void;
}

function fenAfter(fen: string, uci: string): string | null {
  const game = new Chess(fen);
  return game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] }) ? game.fen() : null;
}

export function ResultCard({
  visible, feedbackType, feedbackTitle, feedbackDetail, puzzle,
  bestRevealed, userAttempt, moveHistory, srsSuspended, onPlayBest, onPlayRefutation, onNext,
}: ResultCardProps): preact.JSX.Element | null {
  const ref = useRef<HTMLElement>(null);

  // On stacked layouts the panel sits below the board; bring it into view.
  useEffect(() => {
    if (visible && typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 1080px)').matches) {
      ref.current?.scrollIntoView({ block: 'nearest', behavior: scrollBehavior() });
    }
  }, [visible]);

  if (!visible) return null;

  // Compare against what the player tried, or against the game move when they only asked for the answer.
  const other = feedbackType === 'correct' ? null : userAttempt
    ? { label: t('trainer.result.your_move'), san: userAttempt.san, uci: userAttempt.uci, evalDisplay: userAttempt.evalDisplay }
    : puzzle && { label: t('trainer.result.in_game'), san: puzzle.blunder_san, uci: puzzle.blunder_uci, evalDisplay: puzzle.eval_after_display };

  const otherFen = puzzle && other ? fenAfter(puzzle.fen, other.uci) : null;
  const bestFen = puzzle ? fenAfter(puzzle.fen, puzzle.best_move_uci) : null;

  return (
    <section
      ref={ref}
      id="boardResultCard"
      class="result-panel"
      aria-labelledby="feedbackTitle"
      data-feedback={feedbackType ?? 'revealed'}
      data-best-revealed={String(bestRevealed)}
    >
      <header class="result-panel-header">
        <h2 class="result-panel-title" id="feedbackTitle">{feedbackTitle}</h2>
        <p class="result-panel-detail" id="feedbackDetail">{feedbackDetail}</p>
      </header>

      {puzzle && bestRevealed && (
        <>
          <div class={`result-twins ${otherFen ? '' : 'single'}`}>
            {other && otherFen && (
              <figure class="result-twin">
                <figcaption>
                  <span class="result-twin-label">{other.label}</span>
                  <span class={`result-twin-move ${feedbackType === 'good' ? '' : 'miss'}`}>{other.san} <span class="result-twin-eval">{other.evalDisplay}</span></span>
                </figcaption>
                <MiniBoard
                  fen={otherFen}
                  orientation={puzzle.player_color}
                  move={other.uci}
                  brush="red"
                  label={t('trainer.result.position_after', { move: other.san })}
                />
              </figure>
            )}
            <figure class="result-twin best">
              <figcaption>
                <span class="result-twin-label">{t('trainer.result.best')}</span>
                <span class="result-twin-move">
                  <span id="bestMoveDisplay">{puzzle.best_move_san}</span> <span class="result-twin-eval">{puzzle.eval_before_display}</span>
                </span>
              </figcaption>
              {bestFen && (
                <MiniBoard
                  fen={bestFen}
                  orientation={puzzle.player_color}
                  move={puzzle.best_move_uci}
                  brush="green"
                  label={t('trainer.result.position_after', { move: puzzle.best_move_san })}
                />
              )}
              {puzzle.best_line.length > 1 && (
                <p class="result-line" id="bestLineDisplay">{puzzle.best_line.slice(1).join(' ')}</p>
              )}
            </figure>
          </div>

          {puzzle.explanation_best && (
            <p class="result-panel-text" data-testid="result-best" id="explanationBest">{puzzle.explanation_best}</p>
          )}

          <div class="result-panel-actions">
            {/* eslint-disable-next-line no-restricted-syntax -- btn-success has no <Button> variant; keep until a success variant exists */}
            <button class="btn btn-success" id="tryBestBtn" onClick={onPlayBest}>
              {feedbackType === 'correct' ? t('trainer.button.play_line') : t('trainer.button.play_best')}<kbd>P</kbd>
            </button>
            {puzzle.refutation_line.length > 0 && (
              <Button variant="secondary" testId="show-refutation" onClick={onPlayRefutation}>
                {t('trainer.button.show_refutation')}
              </Button>
            )}
          </div>

          {(puzzle.refutation_line.length > 0 || puzzle.explanation_blunder) && (
            <section class="result-panel-section" data-testid="result-blunder">
              <h3 class="result-panel-section-heading">
                {t('trainer.result.you_played', { move: puzzle.blunder_san })}
                <span class="result-panel-loss">{puzzle.eval_before_display} → {puzzle.eval_after_display}</span>
              </h3>
              {puzzle.refutation_line.length > 0 && (
                <p class="result-line" data-testid="refutation-line">{puzzle.refutation_line.join(' ')}</p>
              )}
              {puzzle.explanation_blunder && (
                <p class="result-panel-text" id="explanationBlunder">{puzzle.explanation_blunder}</p>
              )}
            </section>
          )}

          {puzzle.tactical_pattern && puzzle.tactical_pattern !== 'None' && puzzle.tactical_reason && (
            <details class="result-panel-details" id="tacticalDetails">
              <summary>{t('trainer.details.tactical')}</summary>
              <p class="result-panel-details-heading" id="tacticalInfoTitle">{puzzle.tactical_pattern}</p>
              <p class="result-panel-text" id="tacticalInfoReason">{puzzle.tactical_reason}</p>
            </details>
          )}
        </>
      )}

      {srsSuspended && puzzle && (
        <div class="result-panel-leech" data-testid="srs-leech-hint">
          <a href={`/game/${encodeURIComponent(puzzle.game_id)}`}>{t('trainer.srs.leech_hint')}</a>
        </div>
      )}

      {moveHistory.length > 0 && <div class="move-history">{moveHistory.join(' ')}</div>}

      {/* eslint-disable-next-line no-restricted-syntax -- needs the full-width hook on the button itself; <Button> takes no className */}
      <button class="btn btn-primary result-panel-next" id="overlayNextBtn" onClick={onNext}>
        {t('trainer.shortcuts.next')}<kbd>N</kbd>
      </button>
    </section>
  );
}
