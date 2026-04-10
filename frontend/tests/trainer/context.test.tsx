import { describe, it, expect } from 'vitest';
import { trainerReducer, initialState } from '../../src/trainer/context';

describe('trainerReducer', () => {
  it('sets puzzle data', () => {
    const puzzle = {
      game_id: 'abc', fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      ply: 10, blunder_uci: 'e2e4', blunder_san: 'e4', best_move_uci: 'd2d4',
      best_move_san: 'd4', best_line: ['d4', 'Nf6'], player_color: 'white' as const,
      eval_before: 50, eval_after: -200, eval_before_display: '+0.5',
      eval_after_display: '-2.0', cp_loss: 250, game_phase: 'middlegame',
      tactical_pattern: null, tactical_reason: null, tactical_squares: [],
      explanation_blunder: null, explanation_best: null, game_url: null,
      difficulty: 'medium', pre_move_uci: null, pre_move_fen: null, best_move_eval: 60,
    };
    const state = trainerReducer(initialState, { type: 'SET_PUZZLE', puzzle });
    expect(state.puzzle).toBe(puzzle);
    expect(state.submitted).toBe(false);
    expect(state.bestRevealed).toBe(false);
    expect(state.moveHistory).toEqual([]);
    expect(state.loading).toBe(false);
  });

  it('marks submitted', () => {
    const state = trainerReducer(initialState, { type: 'SET_SUBMITTED' });
    expect(state.submitted).toBe(true);
  });

  it('reveals best move', () => {
    const state = trainerReducer(initialState, { type: 'REVEAL_BEST' });
    expect(state.bestRevealed).toBe(true);
  });

  it('pushes move to history', () => {
    const s1 = trainerReducer(initialState, { type: 'PUSH_MOVE', san: 'e4' });
    expect(s1.moveHistory).toEqual(['e4']);
    const s2 = trainerReducer(s1, { type: 'PUSH_MOVE', san: 'Nf3' });
    expect(s2.moveHistory).toEqual(['e4', 'Nf3']);
  });

  it('pops move from history', () => {
    const s1 = trainerReducer(
      { ...initialState, moveHistory: ['e4', 'Nf3'] },
      { type: 'POP_MOVE' },
    );
    expect(s1.moveHistory).toEqual(['e4']);
  });

  it('sets loading state', () => {
    const state = trainerReducer(initialState, { type: 'SET_LOADING', loading: true });
    expect(state.loading).toBe(true);
  });

  it('sets feedback type', () => {
    const state = trainerReducer(initialState, { type: 'SET_FEEDBACK', feedbackType: 'correct' });
    expect(state.feedbackType).toBe('correct');
  });

  it('resets for new puzzle', () => {
    const dirty = {
      ...initialState,
      submitted: true, bestRevealed: true, moveHistory: ['e4'],
      feedbackType: 'correct' as const, resultVisible: true,
    };
    const state = trainerReducer(dirty, { type: 'RESET_FOR_NEW_PUZZLE' });
    expect(state.submitted).toBe(false);
    expect(state.bestRevealed).toBe(false);
    expect(state.moveHistory).toEqual([]);
    expect(state.feedbackType).toBeNull();
    expect(state.resultVisible).toBe(false);
    expect(state.puzzle).toBeNull();
  });

  it('sets orientation', () => {
    const state = trainerReducer(initialState, { type: 'SET_ORIENTATION', orientation: 'black' });
    expect(state.orientation).toBe('black');
  });

  it('sets fen', () => {
    const fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
    const state = trainerReducer(initialState, { type: 'SET_FEN', fen });
    expect(state.fen).toBe(fen);
  });

  it('toggles result visibility', () => {
    const s1 = trainerReducer(initialState, { type: 'SET_RESULT_VISIBLE', visible: true });
    expect(s1.resultVisible).toBe(true);
    const s2 = trainerReducer(s1, { type: 'SET_RESULT_VISIBLE', visible: false });
    expect(s2.resultVisible).toBe(false);
  });

  it('manages line positions', () => {
    const pos = { fen: 'some-fen', moveHistory: ['e4'] };
    const s1 = trainerReducer(initialState, { type: 'PUSH_LINE_POSITION', position: pos });
    expect(s1.linePositions).toEqual([pos]);
    const s2 = trainerReducer(s1, { type: 'SET_LINE_VIEW_INDEX', index: 0 });
    expect(s2.lineViewIndex).toBe(0);
    const s3 = trainerReducer(s2, { type: 'CLEAR_LINE_NAVIGATION' });
    expect(s3.linePositions).toEqual([]);
    expect(s3.lineViewIndex).toBe(-1);
  });

  it('sets animating flag', () => {
    const state = trainerReducer(initialState, { type: 'SET_ANIMATING', animating: true });
    expect(state.animating).toBe(true);
  });

  it('sets empty state', () => {
    const state = trainerReducer(initialState, { type: 'SET_EMPTY_STATE', emptyState: 'analyzing' });
    expect(state.emptyState).toBe('analyzing');
  });

  it('sets error', () => {
    const state = trainerReducer(initialState, { type: 'SET_ERROR', error: 'failed' });
    expect(state.error).toBe('failed');
  });

  it('toggles shortcuts visibility', () => {
    const s1 = trainerReducer(initialState, { type: 'TOGGLE_SHORTCUTS' });
    expect(s1.shortcutsVisible).toBe(true);
    const s2 = trainerReducer(s1, { type: 'TOGGLE_SHORTCUTS' });
    expect(s2.shortcutsVisible).toBe(false);
  });

  it('sets board flipped', () => {
    const state = trainerReducer(initialState, { type: 'SET_BOARD_FLIPPED', flipped: true });
    expect(state.boardFlipped).toBe(true);
  });

  it('sets starred', () => {
    const state = trainerReducer(initialState, { type: 'SET_STARRED', starred: true });
    expect(state.currentStarred).toBe(true);
  });
});
