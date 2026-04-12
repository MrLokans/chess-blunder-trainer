import { useCallback, useRef, useContext } from 'preact/hooks';
import { TrainerContext } from '../context';

export function useLinePlayer(
  gameRef: preact.RefObject<ChessInstance | null>,
  playFullLine: boolean,
): {
  playBestMove: () => void;
  navigateLine: (direction: 'forward' | 'back') => void;
} {
  const { state, dispatch } = useContext(TrainerContext);
  const animGenRef = useRef(0);

  const playBestMove = useCallback(() => {
    if (state.animating) return;
    const puzzle = state.puzzle;
    const game = gameRef.current;
    if (!puzzle || !game) return;

    const resetGame = new Chess(puzzle.fen);
    gameRef.current = resetGame;
    dispatch({ type: 'SET_FEN', fen: puzzle.fen });
    dispatch({ type: 'CLEAR_LINE_NAVIGATION' });

    dispatch({ type: 'PUSH_LINE_POSITION', position: { fen: puzzle.fen, moveHistory: [] } });

    if (playFullLine && puzzle.best_line.length > 0) {
      const gen = ++animGenRef.current;
      dispatch({ type: 'SET_ANIMATING', animating: true });

      void (async () => {
        const lineGame = new Chess(puzzle.fen);
        const history: string[] = [];

        for (const san of puzzle.best_line) {
          if (animGenRef.current !== gen) break;
          const result = lineGame.move(san);
          if (!result) break;

          history.push(result.san);
          gameRef.current = lineGame;
          dispatch({ type: 'SET_FEN', fen: lineGame.fen() });
          dispatch({ type: 'PUSH_LINE_POSITION', position: { fen: lineGame.fen(), moveHistory: [...history] } });

          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        if (animGenRef.current === gen) {
          dispatch({ type: 'SET_ANIMATING', animating: false });
        }
      })();
    } else {
      const result = resetGame.move(puzzle.best_move_san);
      if (result) {
        gameRef.current = resetGame;
        dispatch({ type: 'SET_FEN', fen: resetGame.fen() });
        dispatch({ type: 'PUSH_MOVE', san: result.san });
        dispatch({ type: 'PUSH_LINE_POSITION', position: { fen: resetGame.fen(), moveHistory: [result.san] } });
      }
    }
  }, [state.animating, state.puzzle, gameRef, playFullLine, dispatch]);

  const navigateLine = useCallback((direction: 'forward' | 'back') => {
    if (state.animating) return;
    const positions = state.linePositions;
    if (positions.length === 0) return;

    const currentIndex = state.lineViewIndex;
    let newIndex: number;

    if (direction === 'back') {
      newIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
    } else {
      newIndex = currentIndex >= positions.length - 1 ? positions.length - 1 : currentIndex + 1;
    }

    if (newIndex === currentIndex) return;

    const pos = positions[newIndex];
    if (!pos) return;

    dispatch({ type: 'SET_LINE_VIEW_INDEX', index: newIndex });
    dispatch({ type: 'SET_FEN', fen: pos.fen });

    const game = new Chess(pos.fen);
    gameRef.current = game;
  }, [state.animating, state.linePositions, state.lineViewIndex, dispatch, gameRef]);

  return { playBestMove, navigateLine };
}
