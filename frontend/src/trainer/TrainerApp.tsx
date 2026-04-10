import { useReducer, useContext, useState, useCallback, useEffect, useRef, useMemo } from 'preact/hooks';
import { TrainerContext, trainerReducer, initialState } from './context';
import { useWebSocket } from '../hooks/useWebSocket';
import { useFeature } from '../hooks/useFeature';
import { useFilters } from './hooks/useFilters';
import { usePuzzle } from './hooks/usePuzzle';
import { useBoardState } from './hooks/useBoardState';
import { useBoardSettings } from './hooks/useBoardSettings';
import { useLinePlayer } from './hooks/useLinePlayer';
import { useKeyboard } from './hooks/useKeyboard';
import { EvalBar } from './components/EvalBar';
import { Board } from './components/Board';
import { VimInput } from './components/VimInput';
import { ContextTags } from './components/ContextTags';
import { BoardPrompt } from './components/BoardPrompt';
import { ResultCard } from './components/ResultCard';
import { FiltersPanel } from './components/FiltersPanel';
import { MoveActions } from './components/MoveActions';
import { PuzzleTools } from './components/PuzzleTools';
import { ShortcutsOverlay } from './components/ShortcutsOverlay';

export function TrainerApp(): preact.JSX.Element {
  const [state, dispatch] = useReducer(trainerReducer, initialState);
  const contextValue = useMemo(() => ({ state, dispatch }), [state, dispatch]);

  return (
    <TrainerContext.Provider value={contextValue}>
      <TrainerCore />
    </TrainerContext.Provider>
  );
}

function TrainerCore(): preact.JSX.Element {
  const { state, dispatch } = useContext(TrainerContext);
  const [submitting, setSubmitting] = useState(false);
  const [vimInputVisible, setVimInputVisible] = useState(false);
  const [userMoveUci, setUserMoveUci] = useState<string | null>(null);
  const [feedbackTitle, setFeedbackTitle] = useState('');
  const [feedbackDetail, setFeedbackDetail] = useState('');
  const gameRef = useRef<ChessInstance | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPuzzleIdRef = useRef<string | null>(null);

  const hasPreMove = useFeature('trainer.pre_move');

  // Sync game from puzzle — synchronous, not in effect
  if (state.puzzle && state.puzzle.game_id !== lastPuzzleIdRef.current) {
    lastPuzzleIdRef.current = state.puzzle.game_id;
    gameRef.current = new Chess(state.puzzle.fen);
  } else if (!state.puzzle && lastPuzzleIdRef.current) {
    lastPuzzleIdRef.current = null;
    gameRef.current = null;
  }

  const puzzleApi = usePuzzle();
  useBoardSettings();

  // Filters — onFilterChange triggers a new puzzle load
  const filtersApi = useFilters(useCallback(() => {
    setUserMoveUci(null);
    void puzzleApi.loadPuzzle(filtersApi.getFilterParams());
  }, [puzzleApi]));

  // Line player
  const { playBestMove, navigateLine } = useLinePlayer(gameRef, filtersApi.state.playFullLine);

  // WebSocket for stats updates
  const ws = useWebSocket(['stats.updated']);
  useEffect(() => {
    const unsub = ws.on('stats.updated', () => {
      if (typeof htmx !== 'undefined') {
        htmx.trigger(document.querySelector('#statsContent') ?? document.body, 'statsUpdate');
      }
    });
    return unsub;
  }, [ws]);

  // Board state (highlights + arrows)
  const { highlights, arrows } = useBoardState(
    gameRef.current,
    filtersApi.state.showArrows,
    filtersApi.state.showThreats,
    filtersApi.state.showTactics,
    userMoveUci,
  );

  // Pre-move animation config
  const animateFrom = useMemo(() => {
    const puzzle = state.puzzle;
    if (!puzzle || !hasPreMove || !puzzle.pre_move_uci || !puzzle.pre_move_fen) return null;
    return {
      fen: puzzle.pre_move_fen,
      from: puzzle.pre_move_uci.slice(0, 2),
      to: puzzle.pre_move_uci.slice(2, 4),
      onComplete: () => dispatch({ type: 'SET_ANIMATING', animating: false }),
    };
  }, [state.puzzle, hasPreMove, dispatch]);

  // Board move handler
  const onBoardMove = useCallback((orig: string, dest: string, move: { san: string; from: string; to: string; promotion?: string }) => {
    if (state.animating) return;
    const game = gameRef.current;
    if (!game) return;

    dispatch({ type: 'SET_FEN', fen: game.fen() });

    if (state.bestRevealed) {
      dispatch({ type: 'PUSH_MOVE', san: move.san });
    } else if (!state.submitted) {
      const puzzle = state.puzzle;
      const uci = move.from + move.to + (move.promotion || '');
      if (puzzle && uci === puzzle.best_move_uci) {
        setTimeout(() => void handleSubmit(), 150);
      }
    }
  }, [state.animating, state.bestRevealed, state.submitted, state.puzzle, dispatch]);

  // Submit move
  const handleSubmit = useCallback(async () => {
    const game = gameRef.current;
    if (!game) return;
    const history = game.history({ verbose: true });
    const lastMove = history[history.length - 1];
    if (!lastMove) return;

    const uci = lastMove.from + lastMove.to + (lastMove.promotion || '');
    setSubmitting(true);
    const data = await puzzleApi.submitMove(uci);
    setSubmitting(false);

    if (!data) {
      setFeedbackTitle(t('trainer.feedback.error'));
      setFeedbackDetail(t('trainer.feedback.submit_failed'));
      dispatch({ type: 'SET_RESULT_VISIBLE', visible: true });
      return;
    }

    if (data.is_best) {
      setFeedbackTitle(t('trainer.feedback.excellent'));
      setFeedbackDetail(t('trainer.feedback.found_best'));
      dispatch({ type: 'SET_FEEDBACK', feedbackType: 'correct' });
    } else if (data.is_blunder) {
      setFeedbackTitle(t('trainer.feedback.same_blunder'));
      setFeedbackDetail(t('trainer.feedback.same_blunder_detail', { userMove: data.user_san }));
      dispatch({ type: 'SET_FEEDBACK', feedbackType: 'blunder' });
    } else {
      const evalDiff = Math.abs(data.user_eval - (state.puzzle?.eval_before ?? 0));
      if (evalDiff < 50) {
        setFeedbackTitle(t('trainer.feedback.good_move'));
        setFeedbackDetail(t('trainer.feedback.good_move_detail', { userMove: data.user_san }));
        dispatch({ type: 'SET_FEEDBACK', feedbackType: 'good' });
      } else {
        setFeedbackTitle(t('trainer.feedback.not_quite'));
        setFeedbackDetail(t('trainer.feedback.not_quite_detail', { userMove: data.user_san, userEval: data.user_eval_display }));
        dispatch({ type: 'SET_FEEDBACK', feedbackType: 'not-quite' });
      }
      setUserMoveUci(data.user_uci);
    }

    dispatch({ type: 'REVEAL_BEST' });
    dispatch({ type: 'SET_RESULT_VISIBLE', visible: true });

    if (typeof htmx !== 'undefined') {
      htmx.trigger(document.body, 'statsUpdate');
    }
  }, [puzzleApi, state.puzzle, dispatch]);

  // Reveal best move
  const handleReveal = useCallback(() => {
    if (state.bestRevealed) {
      dispatch({ type: 'SET_RESULT_VISIBLE', visible: !state.resultVisible });
    } else {
      setFeedbackTitle(t('trainer.feedback.best_revealed'));
      setFeedbackDetail(t('trainer.feedback.best_revealed_detail'));
      dispatch({ type: 'REVEAL_BEST' });
      dispatch({ type: 'SET_RESULT_VISIBLE', visible: true });
    }
  }, [state.bestRevealed, state.resultVisible, dispatch]);

  // Reset position
  const handleReset = useCallback(() => {
    if (state.animating) return;
    const puzzle = state.puzzle;
    if (!puzzle) return;
    gameRef.current = new Chess(puzzle.fen);
    dispatch({ type: 'SET_FEN', fen: puzzle.fen });
    dispatch({ type: 'CLEAR_LINE_NAVIGATION' });
    if (!state.bestRevealed) {
      dispatch({ type: 'SET_RESULT_VISIBLE', visible: false });
    }
  }, [state.animating, state.puzzle, state.bestRevealed, dispatch]);

  // Undo
  const handleUndo = useCallback(() => {
    if (state.animating) return;
    const game = gameRef.current;
    if (!game || game.history().length === 0) return;
    game.undo();
    dispatch({ type: 'SET_FEN', fen: game.fen() });
    dispatch({ type: 'POP_MOVE' });
  }, [state.animating, dispatch]);

  // Flip board
  const handleFlip = useCallback(() => {
    const puzzle = state.puzzle;
    if (!puzzle) return;
    const flipped = !state.boardFlipped;
    dispatch({ type: 'SET_BOARD_FLIPPED', flipped });
    const base = puzzle.player_color === 'black' ? 'black' : 'white';
    dispatch({ type: 'SET_ORIENTATION', orientation: flipped ? (base === 'white' ? 'black' : 'white') : base });
  }, [state.puzzle, state.boardFlipped, dispatch]);

  // Lichess analysis
  const openLichess = useCallback(() => {
    const puzzle = state.puzzle;
    const game = gameRef.current;
    if (!puzzle || !game) return;
    const fen = game.fen().replace(/ /g, '_');
    const lichessArrows: string[] = [];
    if (game.fen() === puzzle.fen) {
      if (puzzle.blunder_uci?.length >= 4) lichessArrows.push(`R${puzzle.blunder_uci.slice(0, 2)}${puzzle.blunder_uci.slice(2, 4)}`);
      if (puzzle.best_move_uci?.length >= 4) lichessArrows.push(`G${puzzle.best_move_uci.slice(0, 2)}${puzzle.best_move_uci.slice(2, 4)}`);
    }
    const hash = lichessArrows.length > 0 ? '#' + lichessArrows.join(',') : '';
    window.open(`https://lichess.org/analysis/${fen}?color=${puzzle.player_color}${hash}`, '_blank');
  }, [state.puzzle]);

  // Next puzzle
  const handleNext = useCallback(() => {
    trackEvent('Puzzle Next');
    setUserMoveUci(null);
    void puzzleApi.loadPuzzle(filtersApi.getFilterParams());
  }, [puzzleApi, filtersApi]);

  // Has move check
  const hasMove = useMemo(() => {
    const game = gameRef.current;
    return !!game && game.history().length > 0;
  }, [state.fen]);

  // Keyboard shortcuts
  useKeyboard({
    submit: handleSubmit,
    next: handleNext,
    reset: handleReset,
    undo: handleUndo,
    flip: handleFlip,
    reveal: handleReveal,
    playBest: playBestMove,
    lichess: openLichess,
    vimInput: () => {
      if (!state.animating && !state.submitted && state.puzzle) {
        setVimInputVisible(true);
      }
    },
    toggleShortcuts: () => dispatch({ type: 'TOGGLE_SHORTCUTS' }),
    navigateLine,
    toggleArrows: () => filtersApi.setShowArrows(!filtersApi.state.showArrows),
    toggleThreats: () => filtersApi.setShowThreats(!filtersApi.state.showThreats),
    isAnimating: state.animating,
    isVimInputActive: vimInputVisible,
    isShortcutsVisible: state.shortcutsVisible,
    isResultVisible: state.resultVisible,
    hideResult: () => dispatch({ type: 'SET_RESULT_VISIBLE', visible: false }),
  });

  // Initial load
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const deepGameId = urlParams.get('game_id');
    const deepPly = urlParams.get('ply');
    if (deepGameId && deepPly) {
      void puzzleApi.loadSpecificPuzzle(deepGameId, deepPly);
    } else {
      void puzzleApi.loadPuzzle(filtersApi.getFilterParams());
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Retry for analyzing state
  useEffect(() => {
    if (state.emptyState === 'analyzing') {
      retryTimerRef.current = setTimeout(() => {
        void puzzleApi.loadPuzzle(filtersApi.getFilterParams());
      }, 5000);
      return () => {
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      };
    }
  }, [state.emptyState, puzzleApi, filtersApi]);

  // Empty state / error
  if (state.emptyState || state.error) {
    return (
      <div class="trainer-page">
        <div class="empty-state" id="emptyState">
          <h2>{state.error || t(`trainer.empty.${state.emptyState}_title`)}</h2>
          <p>{t(`trainer.empty.${state.emptyState || 'default'}_message`)}</p>
          {state.emptyState === 'no_blunders_filtered' ? (
            <button onClick={filtersApi.clearAllFilters}>
              {t('trainer.empty.no_matching_action')}
            </button>
          ) : (
            <a href="/management">{t(`trainer.empty.${state.emptyState || 'default'}_action`)}</a>
          )}
        </div>
      </div>
    );
  }

  const interactive = !state.animating && !state.submitted && !!state.puzzle;

  return (
    <div class="trainer-page">
      <div class="trainer-main" id="trainerLayout">
        <div class="trainer-board-area">
          <ContextTags puzzle={state.puzzle} />
          <div class="board-eval-wrapper">
            {state.puzzle && (
              <EvalBar cp={state.puzzle.eval_before} playerColor={state.puzzle.player_color} />
            )}
            <div id="boardWrapper">
              <Board
                fen={state.fen}
                orientation={state.orientation}
                interactive={interactive}
                coordinates={filtersApi.state.showCoordinates}
                highlights={highlights}
                arrows={arrows}
                gameRef={gameRef}
                onMove={onBoardMove}
                animateFrom={animateFrom}
              />
              <VimInput
            visible={vimInputVisible}
            game={gameRef.current}
            interactive={interactive}
            onMove={(move) => {
              onBoardMove(move.from, move.to, move);
              setVimInputVisible(false);
            }}
            onClose={() => setVimInputVisible(false)}
          />
            </div>
          </div>
          <BoardPrompt
            submitted={state.submitted}
            bestRevealed={state.bestRevealed}
            submitting={submitting}
            hasPuzzle={!!state.puzzle}
          />
          <ResultCard
            visible={state.resultVisible}
            feedbackType={state.feedbackType}
            feedbackTitle={feedbackTitle}
            feedbackDetail={feedbackDetail}
            puzzle={state.puzzle}
            bestRevealed={state.bestRevealed}
            moveHistory={state.moveHistory}
            onPlayBest={playBestMove}
            onNext={handleNext}
            onClose={() => dispatch({ type: 'SET_RESULT_VISIBLE', visible: false })}
          />
        </div>

        <div class="trainer-panel">
          <PuzzleTools
            puzzle={state.puzzle}
            starred={state.currentStarred}
            onStarredChange={(starred) => dispatch({ type: 'SET_STARRED', starred })}
          />
          <MoveActions
            hasPuzzle={!!state.puzzle}
            submitted={state.submitted}
            bestRevealed={state.bestRevealed}
            submitting={submitting}
            hasMove={hasMove}
            onSubmit={handleSubmit}
            onReset={handleReset}
            onReveal={handleReveal}
            onNext={handleNext}
            onUndo={handleUndo}
            onShowShortcuts={() => dispatch({ type: 'TOGGLE_SHORTCUTS' })}
          />
          <FiltersPanel filters={filtersApi} />
        </div>
      </div>

      <ShortcutsOverlay
        visible={state.shortcutsVisible}
        onClose={() => dispatch({ type: 'TOGGLE_SHORTCUTS' })}
      />
    </div>
  );
}
