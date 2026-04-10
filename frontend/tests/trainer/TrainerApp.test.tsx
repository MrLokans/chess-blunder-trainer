import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/preact';

const { mockCg, mockChessground } = vi.hoisted(() => {
  const mockCg = {
    set: vi.fn(),
    setAutoShapes: vi.fn(),
    destroy: vi.fn(),
  };
  return { mockCg, mockChessground: vi.fn(() => mockCg) };
});

vi.mock('@vendor/chessground', () => ({
  Chessground: mockChessground,
}));

vi.mock('../../src/shared/api', () => ({
  client: {
    trainer: {
      getPuzzle: vi.fn().mockResolvedValue({
        game_id: 'test123', fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        ply: 10, blunder_uci: 'e2e4', blunder_san: 'e4',
        best_move_uci: 'd2d4', best_move_san: 'd4', best_line: ['d4'],
        player_color: 'white', eval_before: 50, eval_after: -200,
        eval_before_display: '+0.5', eval_after_display: '-2.0', cp_loss: 250,
        game_phase: 'middlegame', tactical_pattern: null, tactical_reason: null,
        tactical_squares: [], explanation_blunder: null, explanation_best: null,
        game_url: null, difficulty: 'medium', pre_move_uci: null, pre_move_fen: null,
        best_move_eval: 60,
      }),
      getSpecificPuzzle: vi.fn(),
      submitMove: vi.fn(),
    },
    settings: { getBoard: vi.fn().mockResolvedValue({ piece_set: 'cburnett', board_light: '#f0d9b5', board_dark: '#b58863' }) },
    jobs: { list: vi.fn().mockResolvedValue([]) },
    starred: { isStarred: vi.fn().mockResolvedValue({ starred: false }) },
    debug: { gameInfo: vi.fn() },
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(m: string, s: number) { super(m); this.status = s; }
  },
}));

vi.mock('../../src/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({ on: vi.fn(() => vi.fn()) })),
}));

import { TrainerApp } from '../../src/trainer/TrainerApp';

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  window.__features = {};
  (globalThis as Record<string, unknown>).Chess = vi.fn(() => ({
    fen: vi.fn(() => 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'),
    turn: vi.fn(() => 'w'),
    moves: vi.fn(() => []),
    move: vi.fn(),
    undo: vi.fn(),
    history: vi.fn(() => []),
    game_over: vi.fn(() => false),
    in_check: vi.fn(() => false),
    load: vi.fn(() => true),
    board: vi.fn(() => []),
    get: vi.fn(),
    put: vi.fn(),
    remove: vi.fn(),
    pgn: vi.fn(() => ''),
    load_pgn: vi.fn(() => true),
  }));
});

describe('TrainerApp', () => {
  it('renders the trainer layout', async () => {
    render(<TrainerApp />);
    await waitFor(() => {
      expect(document.querySelector('.trainer-page')).not.toBeNull();
    });
  });

  it('loads a puzzle on mount', async () => {
    const { client } = await import('../../src/shared/api');
    render(<TrainerApp />);
    await waitFor(() => {
      expect(client.trainer.getPuzzle).toHaveBeenCalled();
    });
  });
});
