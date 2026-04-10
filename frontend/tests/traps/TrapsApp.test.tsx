import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { TrapsApp } from '../../src/traps/TrapsApp';

vi.mock('../../src/shared/api', () => ({
  client: {
    traps: {
      stats: vi.fn(),
      catalog: vi.fn(),
      detail: vi.fn(),
    },
  },
}));

vi.mock('../../src/shared/dropdown', () => ({
  initDropdowns: vi.fn(),
}));

vi.mock('../../src/shared/sequence-player', () => ({
  default: vi.fn().mockImplementation(() => ({
    setMoves: vi.fn(),
    destroy: vi.fn(),
  })),
}));

const TRAP_STATS = [
  {
    trap_id: 'fried_liver',
    name: 'Fried Liver Attack',
    category: 'attack',
    entered: 5,
    sprung: 3,
    executed: 2,
    last_seen: '2024-03-01',
  },
  {
    trap_id: 'scholars_mate',
    name: "Scholar's Mate",
    category: 'checkmate',
    entered: 2,
    sprung: 1,
    executed: 0,
    last_seen: undefined,
  },
];

const TRAP_SUMMARY = {
  total_sprung: 4,
  total_entered: 7,
  total_executed: 2,
  games_with_traps: 3,
  top_traps: [{ trap_id: 'fried_liver', count: 3 }],
};

const TRAP_CATALOG = [
  { id: 'fried_liver', name: 'Fried Liver Attack' },
  { id: 'scholars_mate', name: "Scholar's Mate" },
];

const TRAP_DETAIL = {
  name: 'Fried Liver Attack',
  victim_side: 'black',
  trap_san: [['e4', 'e5', 'Nf3', 'Nc6']],
  refutation_san: ['d5', 'exd5'],
  mistake_san: 'Nxd5',
  refutation_note: 'The key defensive move.',
  refutation_move: 'd5',
  recognition_tip: 'Watch for Ng5 threatening f7.',
};

describe('TrapsApp', () => {
  let mockStats: ReturnType<typeof vi.fn>;
  let mockCatalog: ReturnType<typeof vi.fn>;
  let mockDetail: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { client } = await import('../../src/shared/api');
    mockStats = vi.mocked(client.traps.stats);
    mockCatalog = vi.mocked(client.traps.catalog);
    mockDetail = vi.mocked(client.traps.detail);

    mockStats.mockResolvedValue({ stats: TRAP_STATS, summary: TRAP_SUMMARY });
    mockCatalog.mockResolvedValue(TRAP_CATALOG);
    mockDetail.mockResolvedValue({ trap: TRAP_DETAIL, history: [] });
  });

  test('shows loading state initially', () => {
    mockStats.mockReturnValue(new Promise(() => {}));
    mockCatalog.mockReturnValue(new Promise(() => {}));
    render(<TrapsApp />);
    const loadingEls = screen.getAllByText(t('common.loading'));
    expect(loadingEls.length).toBeGreaterThan(0);
  });

  test('loads and displays summary stats', async () => {
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText(t('traps.times_fell'))).toBeDefined();
    });

    expect(screen.getByText(t('traps.times_entered'))).toBeDefined();
    expect(screen.getByText(t('traps.times_executed'))).toBeDefined();
    expect(screen.getByText(t('traps.games_involved'))).toBeDefined();

    const statValues = document.querySelectorAll('.stat-value');
    const values = Array.from(statValues).map(el => el.textContent);
    expect(values).toContain('4');
    expect(values).toContain('7');
    expect(values).toContain('2');
    expect(values).toContain('3');
  });

  test('shows empty summary when no data', async () => {
    mockStats.mockResolvedValue({
      stats: [],
      summary: { total_sprung: 0, total_entered: 0, total_executed: 0, games_with_traps: 0 },
    });
    render(<TrapsApp />);

    await waitFor(() => {
      const noDataEls = screen.getAllByText(t('traps.no_data'));
      expect(noDataEls.length).toBeGreaterThan(0);
    });
  });

  test('loads and displays trap list', async () => {
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
      expect(screen.getByText("Scholar's Mate")).toBeDefined();
    });
  });

  test('shows no-data row when no traps after filter', async () => {
    mockStats.mockResolvedValue({
      stats: [],
      summary: { total_sprung: 0, total_entered: 0, total_executed: 0, games_with_traps: 0 },
    });
    render(<TrapsApp />);

    await waitFor(() => {
      const noCells = screen.getAllByText(t('traps.no_data'));
      expect(noCells.length).toBeGreaterThan(0);
    });
  });

  test('selecting a trap opens detail panel', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(mockDetail).toHaveBeenCalledWith('fried_liver');
    });

    await waitFor(() => {
      expect(screen.getByText(t('traps.the_mistake'))).toBeDefined();
    });
  });

  test('close button hides detail panel', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(screen.getByText(t('traps.the_mistake'))).toBeDefined();
    });

    const closeBtn = screen.getByText('×');
    await user.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText(t('traps.the_mistake'))).toBeNull();
    });
  });

  test('shows trap history in detail panel', async () => {
    const user = userEvent.setup();
    mockDetail.mockResolvedValue({
      trap: TRAP_DETAIL,
      history: [
        {
          white: 'Alice',
          black: 'Bob',
          result: '0-1',
          date: '2024-01-10',
          game_url: 'https://lichess.org/abc',
          match_type: 'sprung',
        },
      ],
    });

    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(screen.getByText(/Alice vs Bob/)).toBeDefined();
    });
  });

  test('shows no games message when history is empty', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(screen.getByText(t('traps.no_games'))).toBeDefined();
    });
  });

  test('top traps tags shown in summary', async () => {
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText(t('traps.most_common') + ':')).toBeDefined();
    });

    const tag = document.querySelector('.trap-tag');
    expect(tag?.textContent).toContain('Fried Liver Attack');
    expect(tag?.textContent).toContain('3');
  });

  test('category filter dropdown renders', async () => {
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText(t('traps.filter_category'))).toBeDefined();
    });

    const select = document.querySelector('#trapCategoryFilter') as HTMLSelectElement;
    expect(select).not.toBeNull();
    expect(select.options.length).toBeGreaterThan(1);
  });

  test('category filter changes visible traps', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    const select = document.querySelector('#trapCategoryFilter') as HTMLSelectElement;
    await user.selectOptions(select, 'checkmate');

    await waitFor(() => {
      expect(screen.queryByText('Fried Liver Attack')).toBeNull();
      expect(screen.getByText("Scholar's Mate")).toBeDefined();
    });
  });

  test('shows error on load failure', async () => {
    mockStats.mockRejectedValue(new Error('Network error'));
    mockCatalog.mockRejectedValue(new Error('Network error'));
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText(t('common.error'))).toBeDefined();
    });
  });

  test('board container renders in detail panel', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(document.querySelector('.trap-board-container')).not.toBeNull();
    });
  });

  test('tab switching renders both tab buttons', async () => {
    const user = userEvent.setup();
    render(<TrapsApp />);

    await waitFor(() => {
      expect(screen.getByText('Fried Liver Attack')).toBeDefined();
    });

    await user.click(screen.getAllByText('Fried Liver Attack')[0]);

    await waitFor(() => {
      expect(screen.getByText(t('traps.tab.trap_line'))).toBeDefined();
      expect(screen.getByText(t('traps.tab.refutation_line'))).toBeDefined();
    });
  });
});
