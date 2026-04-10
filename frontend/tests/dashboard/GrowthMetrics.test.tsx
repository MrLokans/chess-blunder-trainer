import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { GrowthMetrics } from '../../src/dashboard/GrowthMetrics';

const makeGrowthData = (overrides: object = {}) => ({
  total_games: 50,
  window_size: 10,
  windows: [
    { avg_blunders_per_game: 2.5, avg_cpl: 80, avg_blunder_severity: 150, clean_game_rate: 30, catastrophic_rate: 10 },
    { avg_blunders_per_game: 2.0, avg_cpl: 70, avg_blunder_severity: 130, clean_game_rate: 40, catastrophic_rate: 8 },
  ],
  trend: {
    blunder_frequency: 'improving',
    move_quality: 'improving',
    severity: 'stable',
    clean_rate: 'improving',
    catastrophic_rate: 'declining',
  },
  ...overrides,
});

vi.mock('../../src/shared/api', () => ({
  client: {
    stats: {
      growth: vi.fn(),
    },
  },
}));

import { client } from '../../src/shared/api';

describe('GrowthMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows loading placeholder initially', () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    render(<GrowthMetrics />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });

  test('renders metric rows after data loads', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.blunders_per_game'))).toBeDefined();
      expect(screen.getByText(t('growth.avg_cpl'))).toBeDefined();
      expect(screen.getByText(t('growth.blunder_severity'))).toBeDefined();
      expect(screen.getByText(t('growth.clean_game_rate'))).toBeDefined();
      expect(screen.getByText(t('growth.catastrophic_rate'))).toBeDefined();
    });
  });

  test('shows no_data message when total_games is 0', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData({ total_games: 0, windows: [] }));
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.no_data'))).toBeDefined();
    });
  });

  test('shows insufficient_data when windows is empty', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData({ total_games: 5, windows: [] }));
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.insufficient_data', { count: 10 }))).toBeDefined();
    });
  });

  test('renders sparkline SVGs for metrics', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    const { container } = render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.blunders_per_game'))).toBeDefined();
    });
    expect(container.querySelectorAll('.growth-sparkline').length).toBe(5);
  });

  test('renders trend arrows', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    const { container } = render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.blunders_per_game'))).toBeDefined();
    });
    expect(container.querySelectorAll('.growth-trend').length).toBeGreaterThan(0);
  });

  test('shows error message on failure', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network error'));
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.load_error'))).toBeDefined();
    });
  });
});
