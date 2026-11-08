import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/preact';

const { mockChessground } = vi.hoisted(() => {
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
        best_move_uci: 'd2d4', best_move_san: 'd4', best_line: ['d4'], refutation_line: [],
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

import { TrainerApp } from '../../src/trainer/TrainerApp';
import { STORAGE_KEYS } from '../../src/shared/storage-keys';

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  window.__features = {};
  (globalThis as Record<string, unknown>).Chess = function () {
    return {
      fen: () => 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      turn: () => 'w',
      moves: () => [],
      move: vi.fn(),
      undo: vi.fn(),
      history: () => [],
      game_over: () => false,
      in_check: () => false,
      load: () => true,
      board: () => [],
      get: vi.fn(),
      put: vi.fn(),
      remove: vi.fn(),
      pgn: () => '',
      load_pgn: () => true,
    };
  };
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

  it('opens on the pattern named in the URL, loads once with it and cleans the URL', async () => {
    const { client } = await import('../../src/shared/api');
    localStorage.setItem(STORAGE_KEYS.trainerColor, 'white');
    localStorage.setItem(STORAGE_KEYS.trainerPhases, JSON.stringify(['endgame']));
    window.history.replaceState(null, '', '/?pattern=hanging_piece');
    render(<TrainerApp />);
    await waitFor(() => {
      expect(client.trainer.getPuzzle).toHaveBeenCalledTimes(1);
    });
    await new Promise((resolve) => { setTimeout(resolve, 50); });
    expect(client.trainer.getPuzzle).toHaveBeenCalledTimes(1);
    expect(vi.mocked(client.trainer.getPuzzle).mock.calls[0]?.[0]).toEqual({ tactical_patterns: ['hanging_piece'] });
    expect(window.location.search).toBe('');
    expect(localStorage.getItem(STORAGE_KEYS.trainerTactical) ?? '').toBe('');
    expect(localStorage.getItem(STORAGE_KEYS.trainerColor)).toBe('white');
    expect(localStorage.getItem(STORAGE_KEYS.trainerPhases)).toBe(JSON.stringify(['endgame']));
    expect(screen.getByTestId('filter-summary').textContent).toBe('trainer.filters.tactical_hanging');
  });

  it('saves the filters shown after a deep link once the drawer changes one of them', async () => {
    localStorage.setItem(STORAGE_KEYS.trainerColor, 'white');
    localStorage.setItem(STORAGE_KEYS.trainerPhases, JSON.stringify(['endgame']));
    window.history.replaceState(null, '', '/?pattern=hanging_piece');
    render(<TrainerApp />);
    fireEvent.click(await screen.findByTestId('change-filters'));
    const dialog = await screen.findByRole('dialog', { name: 'trainer.filters.title' });
    fireEvent.click(dialog.querySelectorAll<HTMLInputElement>('.game-type-filter input')[0] as HTMLInputElement);

    expect(localStorage.getItem(STORAGE_KEYS.trainerTactical)).toBe('hanging_piece');
    expect(localStorage.getItem(STORAGE_KEYS.trainerColor)).toBe('both');
    expect(localStorage.getItem(STORAGE_KEYS.trainerPhases)).toBe(JSON.stringify(['opening', 'middlegame', 'endgame']));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEYS.trainerGameTypes) ?? '[]')).toHaveLength(3);
  });

  it('ignores an unknown pattern in the URL', async () => {
    const { client } = await import('../../src/shared/api');
    window.history.replaceState(null, '', '/?pattern=bogus');
    render(<TrainerApp />);
    await waitFor(() => {
      expect(client.trainer.getPuzzle).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(client.trainer.getPuzzle).mock.calls[0]?.[0]).not.toHaveProperty('tactical_patterns');
    window.history.replaceState(null, '', '/');
  });

  it('loads one new puzzle when the filters drawer closes, not on every change', async () => {
    const { client } = await import('../../src/shared/api');
    render(<TrainerApp />);
    fireEvent.click(await screen.findByTestId('change-filters'));
    const callsBefore = vi.mocked(client.trainer.getPuzzle).mock.calls.length;

    const dialog = await screen.findByRole('dialog', { name: 'trainer.filters.title' });
    const checkboxes = dialog.querySelectorAll<HTMLInputElement>('.game-type-filter input');
    fireEvent.click(checkboxes[0] as HTMLInputElement);
    fireEvent.click(checkboxes[1] as HTMLInputElement);
    expect(client.trainer.getPuzzle).toHaveBeenCalledTimes(callsBefore);

    // loadPuzzle ignores calls within 500ms of the previous load.
    await new Promise((resolve) => { setTimeout(resolve, 550); });
    fireEvent.click(screen.getByTestId('apply-filters'));
    await waitFor(() => {
      expect(client.trainer.getPuzzle).toHaveBeenCalledTimes(callsBefore + 1);
    });
    expect(screen.queryByRole('dialog', { name: 'trainer.filters.title' })).toBeNull();
  });

  it('submits a board move immediately', async () => {
    const { client } = await import('../../src/shared/api');
    const history: Array<{ san: string; from: string; to: string }> = [];
    (globalThis as Record<string, unknown>).Chess = function () {
      return {
        fen: () => 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1',
        turn: () => 'b', moves: () => [],
        move: () => {
          const move = { san: 'e4', from: 'e2', to: 'e4' };
          history.push(move);
          return move;
        },
        undo: vi.fn(), history: () => history, game_over: () => false,
        in_check: () => false, load: () => true, board: () => [], get: vi.fn(),
        put: vi.fn(), remove: vi.fn(), pgn: () => '', load_pgn: () => true,
      };
    };
    vi.mocked(client.trainer.submitMove).mockResolvedValue({
      is_best: true, is_blunder: false, user_san: 'e4', user_eval: 60,
      user_eval_display: '+0.6', user_uci: 'e2e4',
    });

    render(<TrainerApp />);
    await waitFor(() => { expect(mockChessground).toHaveBeenCalled(); });
    const config = mockChessground.mock.calls[0]?.[1] as {
      movable: { events: { after: (orig: string, dest: string) => void } };
    };
    config.movable.events.after('e2', 'e4');

    await waitFor(() => {
      expect(client.trainer.submitMove).toHaveBeenCalledWith(expect.objectContaining({ move: 'e2e4' }));
    });
    await waitFor(() => {
      expect(screen.getByRole('status').textContent).not.toBe('');
    });
  });

  it('opens shortcuts from the toolbar, not the action keys', async () => {
    const { container } = render(<TrainerApp />);

    const shortcutButton = await screen.findByRole('button', { name: 'trainer.shortcuts.title' });
    fireEvent.click(shortcutButton);

    expect(shortcutButton.className).toContain('btn-ghost');
    expect(container.querySelector('.panel-toolbar')).not.toBeNull();
    expect([...container.querySelectorAll('.move-actions kbd')].map((key) => key.textContent)).toEqual(['R', 'B', 'N']);
    const dialog = await screen.findByRole('dialog', { name: 'trainer.shortcuts.title' });
    expect(dialog.contains(document.activeElement)).toBe(true);
    expect(screen.getByRole('button', { name: 'common.close' })).not.toBeNull();
  });

  it('closes the shortcuts dialog with a single Escape and restores focus', async () => {
    render(<TrainerApp />);
    const shortcutButton = await screen.findByRole('button', { name: 'trainer.shortcuts.title' });
    shortcutButton.focus();
    fireEvent.click(shortcutButton);
    await screen.findByRole('dialog');

    fireEvent.keyDown(document.body, { key: 'Escape' });

    await waitFor(() => { expect(screen.queryByRole('dialog')).toBeNull(); });
    expect(document.activeElement).toBe(shortcutButton);
  });
});
