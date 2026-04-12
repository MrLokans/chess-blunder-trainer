import type { PuzzleData } from '../context';

interface ContextTagsProps {
  puzzle: PuzzleData | null;
}

export function ContextTags({ puzzle }: ContextTagsProps): preact.JSX.Element | null {
  if (!puzzle) return null;

  const colorClass = puzzle.player_color === 'white' ? 'white-piece' : 'black-piece';
  const colorText = puzzle.player_color === 'white' ? t('chess.color.white') : t('chess.color.black');
  const phase = puzzle.game_phase;
  const pattern = puzzle.tactical_pattern;
  const hasPattern = pattern && pattern !== 'None';

  return (
    <div class="context-tags">
      <span class="context-tag">
        <span class={`color-indicator ${colorClass}`} />
        <span>{colorText}</span>
      </span>
      <span class="context-tag-separator">&middot;</span>
      {phase && (
        <span class="context-tag phase-highlight">
          {phase.charAt(0).toUpperCase() + phase.slice(1)}
        </span>
      )}
      {hasPattern && (
        <>
          <span class="context-tag-separator">&middot;</span>
          <span class="context-tag">
            <span>{pattern}</span>
          </span>
        </>
      )}
      {puzzle.game_url && (
        <>
          <span class="context-tag-separator">&middot;</span>
          <a href={puzzle.game_url} target="_blank" rel="noopener noreferrer" class="context-tag-link" title={t('trainer.link.original_game')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            {' '}{t('trainer.link.original_game')}
          </a>
        </>
      )}
    </div>
  );
}
