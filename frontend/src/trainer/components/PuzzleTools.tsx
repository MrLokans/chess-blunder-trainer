import { useState, useCallback } from 'preact/hooks';
import { client } from '../../shared/api';
import { useFeature } from '../../hooks/useFeature';
import type { PuzzleData } from '../context';

interface PuzzleToolsProps {
  puzzle: PuzzleData | null;
  starred: boolean;
  onStarredChange: (starred: boolean) => void;
}

export function PuzzleTools({ puzzle, starred, onStarredChange }: PuzzleToolsProps): preact.JSX.Element | null {
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
      const params = puzzle.ply != null ? { ply: puzzle.ply } : {};
      const text = await client.debug.gameInfo(puzzle.game_id, params);
      await navigator.clipboard.writeText(text);
      setCopyLabel(t('trainer.debug.copied'));
      setTimeout(() => setCopyLabel(null), 1500);
    } catch (e) {
      console.error('Copy debug failed:', e);
    }
  }, [puzzle]);

  if (!puzzle) return null;

  const reviewUrl = `/game/${encodeURIComponent(puzzle.game_id)}${puzzle.ply != null ? `?ply=${puzzle.ply}` : ''}`;

  return (
    <div class="panel-section puzzle-tools" id="blunderSection">
      {hasStarred && (
        <button class="btn btn-ghost" id="starPuzzleBtn" onClick={handleStar} title={starred ? t('trainer.star.remove') : t('trainer.star.add')}>
          {starred ? '\u2605' : '\u2606'} {starred ? t('trainer.star.remove') : t('trainer.star.add')}
        </button>
      )}

      {hasDebug && (
        <button class="btn btn-ghost" id="copyDebugBtn" onClick={handleCopyDebug} title={t('trainer.debug.copy_title')}>
          {copyLabel ? `\u2705 ${copyLabel}` : `\ud83d\udccb ${t('trainer.debug.copy')}`}
        </button>
      )}

      {hasGameReview && (
        <a href={reviewUrl} class="btn btn-ghost" id="reviewGameLink">
          {t('game_review.link.review_game')}
        </a>
      )}
    </div>
  );
}
