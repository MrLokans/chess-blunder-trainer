import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { GameReviewApp } from '../../src/game-review/GameReviewApp';

const { mockSequence, mockBoard, mockPlayback } = vi.hoisted(() => {
  const mockSequence = {
    currentIndex: -1,
    length: 3,
    fen: 'startpos',
    isAtStart: true,
    isAtEnd: false,
    lastMove: null,
    goTo: vi.fn(),
    goToStart: vi.fn(),
    goToEnd: vi.fn(),
    stepForward: vi.fn().mockReturnValue({ fen: 'fen2', lastMove: { from: 'e2', to: 'e4' } }),
    stepBack: vi.fn().mockReturnValue({ fen: 'fen1', lastMove: null }),
  };

  const mockBoard = {
    setPosition: vi.fn(),
    setOrientation: vi.fn(),
    destroy: vi.fn(),
  };

  const mockPlayback = {
    isPlaying: false,
    play: vi.fn(),
    pause: vi.fn(),
    toggle: vi.fn(),
    destroy: vi.fn(),
  };

  return { mockSequence, mockBoard, mockPlayback };
});

vi.mock('../../src/shared/api', () => ({
  client: {
    gameReview: {
      getReview: vi.fn(),
    },
    settings: {
      getBoard: vi.fn(),
    },
  },
}));

vi.mock('../../src/shared/sequence-player', () => ({
  MoveSequence: vi.fn().mockImplementation(() => mockSequence),
  ReadOnlyBoard: vi.fn().mockImplementation(() => mockBoard),
  PlaybackController: vi.fn().mockImplementation(() => mockPlayback),
}));

vi.mock('../../src/game-review/eval-chart', () => ({
  EvalChart: vi.fn().mockImplementation(() => ({
    render: vi.fn(),
    setActivePly: vi.fn(),
    onClick: vi.fn(),
    destroy: vi.fn(),
  })),
  evalFromWhite: vi.fn().mockReturnValue(50),
}));

vi.mock('../../src/trainer/board-visuals', () => ({
  applyBoardBackground: vi.fn(),
  applyPieceSet: vi.fn(),
}));

vi.mock('../../src/shared/eval-bar', () => ({
  updateEvalBar: vi.fn(),
}));

const REVIEW_DATA = {
  moves: [
    { san: 'e4', move_number: 1, player: 'white', ply: 1, eval_after: 20, classification: 'normal' },
    { san: 'e5', move_number: 1, player: 'black', ply: 2, eval_after: -10, classification: 'normal' },
    { san: 'Nf3', move_number: 2, player: 'white', ply: 3, eval_after: 30, classification: 'normal' },
  ],
  game: {
    username: 'alice',
    white: 'alice',
    black: 'bob',
    result: '1-0',
    game_url: 'https://lichess.org/abc123',
  },
  analyzed: true,
};

describe('GameReviewApp', () => {
  let mockGetReview: ReturnType<typeof vi.fn>;
  let mockGetBoard: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockSequence.stepForward.mockReturnValue({ fen: 'fen2', lastMove: { from: 'e2', to: 'e4' } });
    mockSequence.stepBack.mockReturnValue({ fen: 'fen1', lastMove: null });

    const { client } = await import('../../src/shared/api');
    mockGetReview = vi.mocked(client.gameReview.getReview);
    mockGetBoard = vi.mocked(client.settings.getBoard);

    mockGetReview.mockResolvedValue(REVIEW_DATA);
    mockGetBoard.mockResolvedValue({ board_light: '#fff', board_dark: '#aaa', piece_set: 'gioco' });
  });

  test('shows loading state initially', () => {
    mockGetReview.mockReturnValue(new Promise(() => {}));
    render(<GameReviewApp gameId="test-game-id" />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });

  test('shows error when gameId is null', async () => {
    render(<GameReviewApp gameId={null} />);
    await waitFor(() => {
      expect(screen.getByText(t('game_review.not_found'))).toBeDefined();
    });
  });

  test('shows error on 404 response', async () => {
    mockGetReview.mockRejectedValue({ status: 404 });
    render(<GameReviewApp gameId="missing-game" />);
    await waitFor(() => {
      expect(screen.getByText(t('game_review.not_found'))).toBeDefined();
    });
  });

  test('shows generic error on non-404 failure', async () => {
    mockGetReview.mockRejectedValue(new Error('Server error'));
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText(t('common.error'))).toBeDefined();
    });
  });

  test('back to trainer link shown on error', async () => {
    render(<GameReviewApp gameId={null} />);
    await waitFor(() => {
      const link = screen.getByText(t('common.back_to_trainer'));
      expect(link).toBeDefined();
    });
  });

  test('loads and displays game metadata', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText(t('chess.color.white'))).toBeDefined();
    });
  });

  test('shows result badge when game has result', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      const badge = document.getElementById('reviewResultBadge');
      expect(badge).not.toBeNull();
    });
  });

  test('shows source link when game has url', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      const link = document.getElementById('reviewSourceLink') as HTMLAnchorElement | null;
      expect(link).not.toBeNull();
      expect(link?.href).toContain('lichess.org');
    });
  });

  test('renders move list with moves', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText('e4')).toBeDefined();
      expect(screen.getByText('e5')).toBeDefined();
      expect(screen.getByText('Nf3')).toBeDefined();
    });
  });

  test('renders board container', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(document.getElementById('reviewBoard')).not.toBeNull();
    });
  });

  test('renders eval chart container when game is analyzed', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(document.getElementById('reviewEvalChartContainer')).not.toBeNull();
    });
  });

  test('does not render eval chart when game is not analyzed', async () => {
    mockGetReview.mockResolvedValue({ ...REVIEW_DATA, analyzed: false });
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText('e4')).toBeDefined();
    });
    expect(document.getElementById('reviewEvalChartContainer')).toBeNull();
    expect(document.getElementById('reviewEvalBarContainer')).toBeNull();
  });

  test('shows no-analysis message when game is not analyzed', async () => {
    mockGetReview.mockResolvedValue({ ...REVIEW_DATA, analyzed: false });
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText(t('game_review.no_analysis'))).toBeDefined();
    });
  });

  test('renders navigation buttons', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(document.getElementById('reviewFirst')).not.toBeNull();
      expect(document.getElementById('reviewPrev')).not.toBeNull();
      expect(document.getElementById('reviewPlayPause')).not.toBeNull();
      expect(document.getElementById('reviewNext')).not.toBeNull();
      expect(document.getElementById('reviewLast')).not.toBeNull();
      expect(document.getElementById('reviewFlip')).not.toBeNull();
    });
  });

  test('flip board button changes orientation label', async () => {
    const user = userEvent.setup();
    render(<GameReviewApp gameId="test-game-id" />);

    await waitFor(() => {
      expect(screen.getByText(t('chess.color.white'))).toBeDefined();
    });

    const flipBtn = document.getElementById('reviewFlip') as HTMLElement;
    await user.click(flipBtn);

    await waitFor(() => {
      expect(screen.getByText(t('chess.color.black'))).toBeDefined();
    });
  });

  test('move number labels rendered', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      const moveNums = document.querySelectorAll('.review-move-num');
      expect(moveNums.length).toBeGreaterThan(0);
      expect(moveNums[0]?.textContent).toContain('1.');
    });
  });

  test('player orientation defaults to white when username matches white', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText(t('chess.color.white'))).toBeDefined();
    });
  });

  test('player orientation is black when username matches black player', async () => {
    mockGetReview.mockResolvedValue({
      ...REVIEW_DATA,
      game: { ...REVIEW_DATA.game, username: 'bob', white: 'alice', black: 'bob' },
    });
    render(<GameReviewApp gameId="test-game-id" />);
    await waitFor(() => {
      expect(screen.getByText(t('chess.color.black'))).toBeDefined();
    });
  });

  test('keyboard left arrow navigates to previous move', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    const { ReadOnlyBoard } = await import('../../src/shared/sequence-player');
    await waitFor(() => {
      expect(vi.mocked(ReadOnlyBoard).mock.calls.length).toBeGreaterThan(0);
    }, { timeout: 200 });

    const callsBefore = mockSequence.stepBack.mock.calls.length;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    expect(mockSequence.stepBack.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  test('keyboard right arrow navigates to next move', async () => {
    render(<GameReviewApp gameId="test-game-id" />);
    const { ReadOnlyBoard } = await import('../../src/shared/sequence-player');
    await waitFor(() => {
      expect(vi.mocked(ReadOnlyBoard).mock.calls.length).toBeGreaterThan(0);
    }, { timeout: 200 });

    const callsBefore = mockSequence.stepForward.mock.calls.length;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    expect(mockSequence.stepForward.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  test('clicking a move in the list navigates to it', async () => {
    const user = userEvent.setup();
    render(<GameReviewApp gameId="test-game-id" />);

    const { ReadOnlyBoard } = await import('../../src/shared/sequence-player');
    await waitFor(() => {
      expect(vi.mocked(ReadOnlyBoard).mock.calls.length).toBeGreaterThan(0);
    }, { timeout: 200 });

    await user.click(screen.getByText('e4'));
    expect(mockSequence.goTo).toHaveBeenCalledWith(0);
  });
});
