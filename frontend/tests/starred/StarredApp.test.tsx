import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { StarredApp } from '../../src/starred/StarredApp';

vi.mock('../../src/shared/api', () => ({
  client: {
    starred: {
      list: vi.fn(),
      unstar: vi.fn(),
    },
  },
}));

vi.mock('../../src/shared/features', () => ({
  hasFeature: vi.fn().mockReturnValue(false),
}));

const STARRED_ITEMS = [
  {
    game_id: 'abc123',
    ply: 24,
    san: 'Nxf7',
    date: '2024-01-15',
    white: 'Alice',
    black: 'Bob',
    cp_loss: 350,
    game_phase: 1,
    note: 'Missed fork',
  },
  {
    game_id: 'def456',
    ply: 10,
    san: 'Bxh7+',
    date: '2024-01-20',
    white: 'Carol',
    black: 'Dave',
    cp_loss: null,
    game_phase: 0,
    note: '',
  },
];

describe('StarredApp', () => {
  let mockList: ReturnType<typeof vi.fn>;
  let mockUnstar: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { client } = await import('../../src/shared/api');
    mockList = vi.mocked(client.starred.list);
    mockUnstar = vi.mocked(client.starred.unstar);
    mockUnstar.mockResolvedValue({});
    window.__features = {};
  });

  test('shows loading state initially', () => {
    mockList.mockReturnValue(new Promise(() => {}));
    render(<StarredApp />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });

  test('loads and displays list of starred puzzles', async () => {
    mockList.mockResolvedValue({ items: STARRED_ITEMS });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText('Nxf7')).toBeDefined();
      expect(screen.getByText('Bxh7+')).toBeDefined();
    });

    expect(screen.getByText('Alice vs Bob')).toBeDefined();
    expect(screen.getByText('Carol vs Dave')).toBeDefined();
    expect(screen.getByText('-3.5')).toBeDefined();
    expect(screen.getByText('Missed fork')).toBeDefined();
  });

  test('shows empty state when no starred puzzles', async () => {
    mockList.mockResolvedValue({ items: [] });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText(t('starred.empty'))).toBeDefined();
    });
  });

  test('shows empty state when items is undefined', async () => {
    mockList.mockResolvedValue({});
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText(t('starred.empty'))).toBeDefined();
    });
  });

  test('click on puzzle link navigates to trainer with params', async () => {
    mockList.mockResolvedValue({ items: STARRED_ITEMS });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText('Nxf7')).toBeDefined();
    });

    const link = screen.getByText('Nxf7').closest('a');
    expect(link).toBeDefined();
    expect(link?.getAttribute('href')).toBe('/?game_id=abc123&ply=24');
  });

  test('unstar button calls API and removes puzzle from list', async () => {
    mockList.mockResolvedValue({ items: STARRED_ITEMS });
    const user = userEvent.setup();
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getAllByTitle(t('starred.unstar'))).toHaveLength(2);
    });

    const unstarButtons = screen.getAllByTitle(t('starred.unstar'));
    await user.click(unstarButtons[0]);

    await waitFor(() => {
      expect(mockUnstar).toHaveBeenCalledWith('abc123', 24);
    });

    expect(screen.queryByText('Nxf7')).toBeNull();
    expect(screen.getByText('Bxh7+')).toBeDefined();
  });

  test('shows empty state after last puzzle is unstarred', async () => {
    mockList.mockResolvedValue({ items: [STARRED_ITEMS[0]] });
    const user = userEvent.setup();
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByTitle(t('starred.unstar'))).toBeDefined();
    });

    await user.click(screen.getByTitle(t('starred.unstar')));

    await waitFor(() => {
      expect(screen.getByText(t('starred.empty'))).toBeDefined();
    });
  });

  test('shows error message on load failure', async () => {
    mockList.mockRejectedValue(new Error('Network error'));
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeDefined();
    });
  });

  test('displays phase labels correctly', async () => {
    mockList.mockResolvedValue({ items: STARRED_ITEMS });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText('chess.phase.middlegame')).toBeDefined();
      expect(screen.getByText('chess.phase.opening')).toBeDefined();
    });
  });

  test('shows em-dash for missing cp_loss', async () => {
    mockList.mockResolvedValue({ items: [STARRED_ITEMS[1]] });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText('\u2014')).toBeDefined();
    });
  });

  test('game review link hidden when feature disabled', async () => {
    mockList.mockResolvedValue({ items: STARRED_ITEMS });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText('Nxf7')).toBeDefined();
    });

    expect(screen.queryByText(t('game_review.link.review_game'))).toBeNull();
  });

  test('game review link shown when feature enabled', async () => {
    const { hasFeature } = await import('../../src/shared/features');
    vi.mocked(hasFeature).mockReturnValue(true);

    mockList.mockResolvedValue({ items: [STARRED_ITEMS[0]] });
    render(<StarredApp />);

    await waitFor(() => {
      expect(screen.getByText(t('game_review.link.review_game'))).toBeDefined();
    });

    const reviewLink = screen.getByText(t('game_review.link.review_game')).closest('a');
    expect(reviewLink?.getAttribute('href')).toBe('/game/abc123?ply=24');
  });
});
