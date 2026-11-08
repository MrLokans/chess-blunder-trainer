import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { DashboardApp } from '../../src/dashboard/DashboardApp';

vi.mock('../../src/shared/api', async (importActual) => {
  const actual = await importActual<typeof import('../../src/shared/api')>();
  return {
  ApiError: actual.ApiError,
  isAbortError: actual.isAbortError,
  client: {
    stats: {
      overview: vi.fn().mockResolvedValue({ total_games: 100, analyzed_games: 80, pending_analysis: 20, total_blunders: 25 }),
      gameBreakdown: vi.fn().mockResolvedValue({
        items: [{ source: 'lichess', username: 'player', total_games: 137, analyzed_games: 137, pending_games: 0 }],
      }),
      gamesByDate: vi.fn().mockResolvedValue({ items: [] }),
      gamesByHour: vi.fn().mockResolvedValue({ items: [] }),
      blundersByPhase: vi.fn().mockResolvedValue({ total_blunders: 0, by_phase: [] }),
      blundersByColor: vi.fn().mockResolvedValue({ total_blunders: 0, by_color: [] }),
      blundersByGameType: vi.fn().mockResolvedValue({ total_blunders: 0, by_game_type: [] }),
      blundersByEco: vi.fn().mockResolvedValue({ total_blunders: 0, by_opening: [] }),
      blundersByTacticalPattern: vi.fn().mockResolvedValue({ total_blunders: 0, by_pattern: [] }),
      blundersByDifficulty: vi.fn().mockResolvedValue({ total_blunders: 0, by_difficulty: [] }),
      collapsePoint: vi.fn().mockResolvedValue({ avg_collapse_move: null, median_collapse_move: null, total_games_with_blunders: 0, total_games_without_blunders: 0, distribution: [] }),
      conversionResilience: vi.fn().mockResolvedValue({ games_with_advantage: 0, games_converted: 0, conversion_rate: 0, games_with_disadvantage: 0, games_saved: 0, resilience_rate: 0 }),
      growth: vi.fn().mockResolvedValue({
        total_games: 100,
        window_size: 20,
        windows: [1.5, 1.8, 2.0, 2.4, 2.6].map((bpg, i) => ({
          window_index: i, game_start: i * 20 + 1, game_end: i * 20 + 20, avg_blunders_per_game: bpg,
          avg_cpl: 80, avg_blunder_severity: 500, clean_game_rate: 20, catastrophic_rate: 30,
        })),
      }),
    },
    analysis: {
      status: vi.fn().mockResolvedValue({ status: 'idle' }),
      start: vi.fn().mockResolvedValue({}),
    },
    traps: {
      stats: vi.fn().mockResolvedValue({ summary: { total_sprung: 0, total_entered: 0 }, stats: [] }),
    },
  },
  };
});

vi.mock('../../src/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    on: () => () => {},
  }),
}));

describe('DashboardApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.__features = {};
  });

  test('summarises the library and leads with the trend', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('library-status').textContent).toContain(t('dashboard.status.games', { count: 100 }));
    });
    expect(screen.getByRole('heading', { level: 2, name: t('dashboard.trend.verdict.declining') })).toBeDefined();
  });

  test('passes the dashboard filters to the growth trend', async () => {
    const { client } = await import('../../src/shared/api');
    render(<DashboardApp />);
    await waitFor(() => { expect(vi.mocked(client.stats.growth)).toHaveBeenCalled(); });
    expect(vi.mocked(client.stats.growth).mock.calls[0]?.[0]).toEqual(vi.mocked(client.stats.overview).mock.calls[0]?.[0]);
  });

  test('sends the browser timezone for hourly accuracy', async () => {
    const { client } = await import('../../src/shared/api');
    render(<DashboardApp />);

    await waitFor(() => {
      expect(vi.mocked(client.stats.gamesByHour)).toHaveBeenCalledWith(expect.objectContaining({
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }));
    });
  });

  test('renders filter bar', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.filter.title'))).toBeDefined();
    });
  });

  test('follows the trend with where-from, practice and game-flow sections, without the library table', async () => {
    window.__features = { 'dashboard.heatmap': true };
    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.section.where_from'))).toBeDefined();
    });

    const headings = Array.from(container.querySelectorAll('.dashboard-section > h2')).map(h => h.textContent);
    expect(headings).toEqual([
      t('dashboard.section.where_from'),
      t('dashboard.section.practice'),
      t('dashboard.section.game_flow'),
    ]);
    expect(container.querySelector('.dashboard-section .dashboard-scope-note')?.textContent).toBe(t('dashboard.scope.unfiltered'));
    expect(screen.queryByText(t('dashboard.chart.game_breakdown'))).toBeNull();
  });

  test('puts hour-of-day accuracy last', async () => {
    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.chart.accuracy_by_hour'))).toBeDefined();
    });
    const titles = Array.from(container.querySelectorAll('.chart-title')).map(el => el.textContent);
    expect(titles.at(-1)).toBe(t('dashboard.chart.accuracy_by_hour'));
  });

  test('feature-gated sections hidden when disabled', async () => {
    window.__features = {
      'dashboard.accuracy': false,
      'dashboard.phase_breakdown': false,
      'dashboard.tactical_breakdown': false,
      'dashboard.collapse_point': false,
      'dashboard.conversion_resilience': false,
      'dashboard.opening_breakdown': false,
      'dashboard.difficulty_breakdown': false,
      'dashboard.traps': false,
      'dashboard.growth': false,
      'dashboard.heatmap': false,
    };

    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('coaching-action')).toBeDefined();
    });

    expect(container.querySelector('.trend-spine')).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.accuracy_by_date'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.blunders_by_phase'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.blunders_by_tactical'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.collapse_point'))).toBeNull();
  });

  test('puts the next step beside the trend, under the filters and library status', async () => {
    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('coaching-action')).toBeDefined();
    });

    const card = screen.getByTestId('coaching-action');
    expect(card.dataset.action).toBe('train');

    const order = Array.from(
      container.querySelectorAll('.dashboard-filter-bar, .library-status, .trend-spine'),
    );
    expect(order.map(el => ['dashboard-filter-bar', 'library-status', 'trend-spine']
      .find(name => el.classList.contains(name))))
      .toEqual(['dashboard-filter-bar', 'library-status', 'trend-spine']);
    expect(card.closest('.trend-spine__side')).not.toBeNull();
  });

  test('coaching action falls back to the blunder total when breakdowns are off', async () => {
    window.__features = {
      'dashboard.phase_breakdown': false,
      'dashboard.tactical_breakdown': false,
    };

    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('coaching-action')).toBeDefined();
    });

    expect(screen.getByText(t('dashboard.coach.evidence.overall'))).toBeDefined();
    expect(screen.getByText(t('dashboard.coach.evidence.count', { count: 25 }))).toBeDefined();
  });

  test('offers exactly one retry when analysis failed with nothing to train', async () => {
    const { client } = await import('../../src/shared/api');
    vi.mocked(client.stats.overview).mockResolvedValue({ total_games: 100, analyzed_games: 80, pending_analysis: 20, total_blunders: 0 });
    vi.mocked(client.analysis.status).mockResolvedValue({ status: 'failed' });

    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('coaching-action').dataset.action).toBe('analysis_failed');
    });

    expect(screen.getAllByText(t('dashboard.coach.analysis_failed.cta'))).toHaveLength(1);
    expect(container.querySelector('[data-testid="analysis-status"] button')).toBeNull();
  });

  test('keeps the status-line retry when the card is recommending training', async () => {
    const { client } = await import('../../src/shared/api');
    // Both mocks set explicitly: clearAllMocks resets calls, not implementations.
    vi.mocked(client.stats.overview).mockResolvedValue({ total_games: 100, analyzed_games: 80, pending_analysis: 20, total_blunders: 25 });
    vi.mocked(client.analysis.status).mockResolvedValue({ status: 'failed' });

    const { container } = render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByTestId('coaching-action').dataset.action).toBe('train');
    });

    expect(container.querySelector('[data-testid="analysis-status"] button')).not.toBeNull();
  });

  test('shows canonical loading state initially', () => {
    const { container } = render(<DashboardApp />);
    const loading = container.querySelector('div.loading');
    expect(loading).not.toBeNull();
    expect(loading?.textContent).toBe(t('common.loading'));
  });

  test('shows Alert error on load failure', async () => {
    const { client } = await import('../../src/shared/api');
    vi.mocked(client.stats.overview).mockRejectedValueOnce(new Error('Network down'));

    const { container } = render(<DashboardApp />);

    await waitFor(() => {
      const alert = container.querySelector('.alert.alert-error');
      expect(alert).not.toBeNull();
      expect(alert?.textContent).toContain('Network down');
    });
  });
});
