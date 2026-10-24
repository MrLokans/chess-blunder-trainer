import { useCallback, useEffect, useRef, useContext } from 'preact/hooks';
import { TrainerContext } from '../context';

export function useLinePlayer(
  gameRef: preact.RefObject<ChessInstance | null>,
): {
  playBestMove: () => void;
  playRefutation: () => void;
  navigateLine: (direction: 'forward' | 'back') => void;
} {
  const { state, dispatch } = useContext(TrainerContext);
  const animGenRef = useRef(0);

  // A new puzzle cancels a line still animating, so it can't move pieces on the new board.
  useEffect(() => { animGenRef.current++; }, [state.puzzle]);

  const animateLine = useCallback((moves: string[]) => {
    const puzzle = state.puzzle;
    if (!puzzle) return;
    const gen = ++animGenRef.current;
    dispatch({ type: 'SET_ANIMATING', animating: true });

    void (async () => {
      const lineGame = new Chess(puzzle.fen);
      const history: string[] = [];

      for (const san of moves) {
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
  }, [state.puzzle, gameRef, dispatch]);

  const resetToPuzzle = useCallback((): ChessInstance | null => {
    const puzzle = state.puzzle;
    if (state.animating || !puzzle || !gameRef.current) return null;

    const resetGame = new Chess(puzzle.fen);
    gameRef.current = resetGame;
    dispatch({ type: 'SET_FEN', fen: puzzle.fen });
    dispatch({ type: 'CLEAR_LINE_NAVIGATION' });
    dispatch({ type: 'PUSH_LINE_POSITION', position: { fen: puzzle.fen, moveHistory: [] } });
    return resetGame;
  }, [state.animating, state.puzzle, gameRef, dispatch]);

  const playBestMove = useCallback(() => {
    const resetGame = resetToPuzzle();
    const puzzle = state.puzzle;
    if (!resetGame || !puzzle) return;

    if (puzzle.best_line.length > 0) {
      animateLine(puzzle.best_line);
    } else {
      const result = resetGame.move(puzzle.best_move_san);
      if (result) {
        dispatch({ type: 'SET_FEN', fen: resetGame.fen() });
        dispatch({ type: 'PUSH_MOVE', san: result.san });
        dispatch({ type: 'PUSH_LINE_POSITION', position: { fen: resetGame.fen(), moveHistory: [result.san] } });
      }
    }
  }, [resetToPuzzle, animateLine, state.puzzle, dispatch]);

  const playRefutation = useCallback(() => {
    const puzzle = state.puzzle;
    if (!puzzle || puzzle.refutation_line.length === 0 || !resetToPuzzle()) return;
    animateLine([puzzle.blunder_san, ...puzzle.refutation_line]);
  }, [resetToPuzzle, animateLine, state.puzzle]);

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

  return { playBestMove, playRefutation, navigateLine };
}
