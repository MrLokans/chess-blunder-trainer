import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { DashboardApp } from '../../src/dashboard/DashboardApp';

vi.mock('../../src/shared/api', () => ({
  client: {
    stats: {
      overview: vi.fn().mockResolvedValue({ total_games: 100, analyzed_games: 80, total_blunders: 25 }),
      gameBreakdown: vi.fn().mockResolvedValue({ items: [] }),
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
    },
    analysis: {
      status: vi.fn().mockResolvedValue({ status: 'idle' }),
      start: vi.fn().mockResolvedValue({}),
    },
    traps: {
      stats: vi.fn().mockResolvedValue({ summary: { total_sprung: 0, total_entered: 0 }, stats: [] }),
    },
  },
}));

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

  test('renders stats after loading', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText('100')).toBeDefined();
      expect(screen.getByText('80')).toBeDefined();
      expect(screen.getByText('25')).toBeDefined();
    });
  });

  test('renders filter bar', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.filter.title'))).toBeDefined();
    });
  });

  test('renders game breakdown table', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.chart.game_breakdown'))).toBeDefined();
    });
  });

  test('renders management link', async () => {
    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText(t('dashboard.link.manage_imports'))).toBeDefined();
    });
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

    render(<DashboardApp />);
    await waitFor(() => {
      expect(screen.getByText('100')).toBeDefined();
    });

    expect(screen.queryByText(t('dashboard.chart.accuracy_by_date'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.blunders_by_phase'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.blunders_by_tactical'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.collapse_point'))).toBeNull();
    expect(screen.queryByText(t('dashboard.chart.growth'))).toBeNull();
  });

  test('shows loading state initially', () => {
    render(<DashboardApp />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });
});
