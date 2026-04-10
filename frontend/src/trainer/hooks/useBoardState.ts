import { useMemo, useContext } from 'preact/hooks';
import { TrainerContext } from '../context';
import {
  buildBlunderHighlight, buildBestMoveHighlight, buildUserMoveHighlight,
  buildTacticalHighlights, mergeHighlights,
} from '../highlights';
import type { HighlightMap } from '../highlights';
import { buildThreatHighlights } from '../threats';

export interface Arrow {
  from: string;
  to: string;
  color: string;
}

interface BoardStateResult {
  highlights: HighlightMap;
  arrows: Arrow[];
}

export function useBoardState(
  game: ChessInstance | null,
  showArrows: boolean,
  showThreats: boolean,
  showTactics: boolean,
  userMoveUci: string | null,
): BoardStateResult {
  const { state } = useContext(TrainerContext);
  const { puzzle, bestRevealed, fen } = state;

  const highlights = useMemo((): HighlightMap => {
    const maps: HighlightMap[] = [buildBlunderHighlight(puzzle)];

    if (bestRevealed) {
      maps.push(buildBestMoveHighlight(puzzle));
    }

    if (showThreats && game) {
      maps.push(buildThreatHighlights(game, true));
    }

    if (showTactics && bestRevealed) {
      maps.push(buildTacticalHighlights(puzzle, game, bestRevealed, showTactics));
    }

    if (userMoveUci) {
      maps.push(buildUserMoveHighlight(userMoveUci));
    }

    return mergeHighlights(...maps);
  }, [puzzle, bestRevealed, fen, game, showThreats, showTactics, userMoveUci]);

  const arrows = useMemo((): Arrow[] => {
    if (!showArrows || !puzzle) return [];
    const result: Arrow[] = [];

    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      result.push({
        from: puzzle.blunder_uci.slice(0, 2),
        to: puzzle.blunder_uci.slice(2, 4),
        color: 'red',
      });
    }

    if (bestRevealed && puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      result.push({
        from: puzzle.best_move_uci.slice(0, 2),
        to: puzzle.best_move_uci.slice(2, 4),
        color: 'green',
      });
    }

    return result;
  }, [showArrows, puzzle, bestRevealed]);

  return { highlights, arrows };
}
