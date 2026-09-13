import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { GrowthMetrics } from '../../src/dashboard/GrowthMetrics';

const makeGrowthData = (overrides: object = {}) => ({
  total_games: 50,
  window_size: 20,
  windows: [
    { window_index: 0, game_start: 1, game_end: 20, avg_blunders_per_game: 2.5, avg_cpl: 80, avg_blunder_severity: 150, clean_game_rate: 30, catastrophic_rate: 10 },
    { window_index: 1, game_start: 21, game_end: 40, avg_blunders_per_game: 2.0, avg_cpl: 70, avg_blunder_severity: 130, clean_game_rate: 40, catastrophic_rate: 8 },
  ],
  trend: {
    blunder_frequency: 'improving', move_quality: 'improving', severity: 'stable', clean_rate: 'improving', catastrophic_rate: 'declining',
  },
  ...overrides,
});

vi.mock('../../src/shared/api', () => ({ client: { stats: { growth: vi.fn() } } }));
import { client } from '../../src/shared/api';

describe('GrowthMetrics', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test('shows loading placeholder initially', () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    render(<GrowthMetrics />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });

  test('renders metric values and labeled trends', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(makeGrowthData());
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.blunders_per_game'))).toBeDefined();
      expect(screen.getAllByLabelText(t('growth.improving'))).toHaveLength(3);
    });
    expect(screen.getByText(/70.*CP/)).toBeDefined();
    expect(screen.getByText(/130.*CP/)).toBeDefined();
  });

  test('does not imply a trend for one complete window', async () => {
    const data = makeGrowthData({ windows: [makeGrowthData().windows[0]], trend: undefined });
    (client.stats.growth as ReturnType<typeof vi.fn>).mockResolvedValue(data);
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.blunders_per_game'))).toBeDefined();
    });
    expect(screen.queryByLabelText(t('growth.improving'))).toBeNull();
  });

  test('shows no-data and insufficient-data states', async () => {
    const growth = client.stats.growth as ReturnType<typeof vi.fn>;
    growth.mockResolvedValueOnce(makeGrowthData({ total_games: 0, windows: [] }));
    const { rerender } = render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.no_data'))).toBeDefined();
    });
    growth.mockResolvedValueOnce(makeGrowthData({ total_games: 5, windows: [] }));
    rerender(<GrowthMetrics params={{ start_date: '2025-01-01' }} />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.insufficient_data', { count: 20 }))).toBeDefined();
    });
  });

  test('shows error message on failure', async () => {
    (client.stats.growth as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network error'));
    render(<GrowthMetrics />);
    await waitFor(() => {
      expect(screen.getByText(t('growth.load_error'))).toBeDefined();
    });
  });
});
