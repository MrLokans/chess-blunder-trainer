import { useState, useCallback } from 'preact/hooks';
import { client } from '../../shared/api';
import { useFeature } from '../../hooks/useFeature';
import { Button } from '../../components/primitives/Button';
import type { PuzzleData } from '../context';

interface PuzzleToolsProps {
  puzzle: PuzzleData | null;
  starred: boolean;
  onStarredChange: (starred: boolean) => void;
  onShowShortcuts: () => void;
}

export function PuzzleTools({ puzzle, starred, onStarredChange, onShowShortcuts }: PuzzleToolsProps): preact.JSX.Element | null {
  const [copyLabel, setCopyLabel] = useState<string | null>(null);
  const hasDebug = useFeature('debug.copy');
  const hasGameReview = useFeature('page.game_review');
  const hasStarred = useFeature('starred.puzzles');

  const handleStar = useCallback(async () => {
    if (!puzzle) return;
    try {
      if (starred) {
        await client.starred.unstar(puzzle.game_id, puzzle.ply);
        onStarredChange(false);
      } else {
        await client.starred.star(puzzle.game_id, puzzle.ply);
        onStarredChange(true);
      }
    } catch (e) {
      console.error('Star toggle failed:', e);
    }
  }, [puzzle, starred, onStarredChange]);

  const handleCopyDebug = useCallback(async () => {
    if (!puzzle) return;
    try {
      const params = { ply: puzzle.ply };
      const text = await client.debug.gameInfo(puzzle.game_id, params);
      await navigator.clipboard.writeText(text);
      setCopyLabel(t('trainer.debug.copied'));
      setTimeout(() => { setCopyLabel(null); }, 1500);
    } catch (e) {
      console.error('Copy debug failed:', e);
    }
  }, [puzzle]);

  if (!puzzle) return null;

  const reviewUrl = `/game/${encodeURIComponent(puzzle.game_id)}?ply=${String(puzzle.ply)}`;

  return (
    <div class="panel-toolbar" id="blunderSection">
      {hasStarred && (
        // eslint-disable-next-line no-restricted-syntax -- needs a visible title tooltip; <Button> exposes no title prop
        <button class="btn btn-ghost" id="starPuzzleBtn" onClick={() => { void handleStar(); }} aria-label={starred ? t('trainer.star.remove') : t('trainer.star.add')} title={starred ? t('trainer.star.remove') : t('trainer.star.add')}>
          {starred ? '\u2605' : '\u2606'}
        </button>
      )}

      {hasDebug && (
        // eslint-disable-next-line no-restricted-syntax -- needs a visible title tooltip; <Button> exposes no title prop
        <button class="btn btn-ghost" id="copyDebugBtn" onClick={() => { void handleCopyDebug(); }} aria-label={t('trainer.debug.copy_title')} title={t('trainer.debug.copy_title')}>
          {copyLabel ? `✓ ${copyLabel}` : <svg class="toolbar-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="8" width="10" height="12" /><path d="M15 8V4H5v12h4" /></svg>}
        </button>
      )}

      {hasGameReview && (
        // eslint-disable-next-line no-restricted-syntax -- navigational anchor, not a <button>; <Button> renders only <button>
        <a href={reviewUrl} class="btn btn-ghost" id="reviewGameLink" aria-label={t('game_review.link.review_game')} title={t('game_review.link.review_game')}>
          ↗
        </a>
      )}

      <Button variant="ghost" size="sm" ariaLabel={t('trainer.shortcuts.title')} onClick={onShowShortcuts}>?</Button>
    </div>
  );
}
