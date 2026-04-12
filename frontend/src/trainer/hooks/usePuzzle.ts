import { useCallback, useRef, useContext } from 'preact/hooks';
import { client, ApiError } from '../../shared/api';
import { TrainerContext } from '../context';
import type { SubmitMoveResponse } from '../../types/api';
import type { QueryParams } from './useFilters';

export interface PuzzleAPI {
  loadPuzzle: (filterParams?: QueryParams) => Promise<void>;
  loadSpecificPuzzle: (gameId: string, ply: string) => Promise<void>;
  submitMove: (uci: string) => Promise<SubmitMoveResponse | null>;
}

async function hasActiveJobs(): Promise<boolean> {
  try {
    const jobs = await client.jobs.list({ status: 'running' });
    if (Array.isArray(jobs) && jobs.length > 0) return true;
    const pending = await client.jobs.list({ status: 'pending' });
    return Array.isArray(pending) && pending.length > 0;
  } catch {
    return false;
  }
}

export function usePuzzle(): PuzzleAPI {
  const { state, dispatch } = useContext(TrainerContext);
  const cooldownRef = useRef(false);

  const loadPuzzle = useCallback(async (filterParams?: QueryParams) => {
    if (cooldownRef.current) return;
    cooldownRef.current = true;
    setTimeout(() => { cooldownRef.current = false; }, 500);

    dispatch({ type: 'RESET_FOR_NEW_PUZZLE' });
    dispatch({ type: 'SET_LOADING', loading: true });

    try {
      const data = await client.trainer.getPuzzle(filterParams);
      dispatch({ type: 'SET_PUZZLE', puzzle: data });
      dispatch({ type: 'SET_FEN', fen: data.fen });
      dispatch({ type: 'SET_ORIENTATION', orientation: data.player_color === 'black' ? 'black' : 'white' });
      trackEvent('Puzzle Loaded', {
        phase: data.game_phase || '',
        color: data.player_color,
        difficulty: data.difficulty || '',
        tactical_pattern: data.tactical_pattern || '',
      });
    } catch (err) {
      dispatch({ type: 'SET_LOADING', loading: false });
      if (err instanceof ApiError) {
        const msg = err.message.toLowerCase();
        if (msg.includes('no games found')) {
          const active = await hasActiveJobs();
          dispatch({ type: 'SET_EMPTY_STATE', emptyState: active ? 'analyzing' : 'no_games' });
        } else if (msg.includes('no blunders found')) {
          const active = await hasActiveJobs();
          dispatch({ type: 'SET_EMPTY_STATE', emptyState: active ? 'analyzing' : 'no_blunders' });
        } else {
          dispatch({ type: 'SET_ERROR', error: err.message });
        }
      } else {
        console.error('Failed to load puzzle:', err);
        dispatch({ type: 'SET_ERROR', error: t('common.error') });
      }
    }
  }, [dispatch]);

  const loadSpecificPuzzle = useCallback(async (gameId: string, ply: string) => {
    dispatch({ type: 'RESET_FOR_NEW_PUZZLE' });
    dispatch({ type: 'SET_LOADING', loading: true });

    try {
      const data = await client.trainer.getSpecificPuzzle(gameId, parseInt(ply, 10));
      dispatch({ type: 'SET_PUZZLE', puzzle: data });
      dispatch({ type: 'SET_FEN', fen: data.fen });
      dispatch({ type: 'SET_ORIENTATION', orientation: data.player_color === 'black' ? 'black' : 'white' });
    } catch (err) {
      console.error('Failed to load specific puzzle:', err);
      dispatch({ type: 'SET_ERROR', error: t('common.error') });
      dispatch({ type: 'SET_LOADING', loading: false });
    }
  }, [dispatch]);

  const submitMove = useCallback(async (uci: string): Promise<SubmitMoveResponse | null> => {
    const puzzle = state.puzzle;
    if (!puzzle) return null;

    const payload = {
      move: uci,
      fen: puzzle.fen || '',
      game_id: puzzle.game_id || '',
      ply: puzzle.ply || 0,
      blunder_uci: puzzle.blunder_uci || '',
      blunder_san: puzzle.blunder_san || '',
      best_move_uci: puzzle.best_move_uci || '',
      best_move_san: puzzle.best_move_san || '',
      best_line: puzzle.best_line,
      player_color: puzzle.player_color,
      eval_after: puzzle.eval_after || 0,
      best_move_eval: puzzle.best_move_eval ?? null,
    };

    try {
      const data = await client.trainer.submitMove(payload);
      dispatch({ type: 'SET_SUBMITTED' });
      trackEvent('Puzzle Submitted', {
        result: data.is_best ? 'correct' : 'incorrect',
        phase: puzzle.game_phase || '',
        difficulty: puzzle.difficulty || '',
      });
      return data;
    } catch (err) {
      console.error('Submit failed:', err);
      return null;
    }
  }, [state.puzzle, dispatch]);

  return { loadPuzzle, loadSpecificPuzzle, submitMove };
}
