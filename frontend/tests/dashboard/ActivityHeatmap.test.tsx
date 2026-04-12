import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { ActivityHeatmap } from '../../src/dashboard/ActivityHeatmap';

const MOCK_HEATMAP_DATA = {
  daily_counts: {
    '2025-03-15': { total: 12, correct: 8, incorrect: 4 },
    '2025-04-01': { total: 3, correct: 2, incorrect: 1 },
  },
  total_days: 2,
  total_attempts: 15,
};

vi.mock('../../src/shared/api', () => ({
  client: {
    stats: {
      activityHeatmap: vi.fn(),
    },
  },
}));

describe('ActivityHeatmap', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { client } = await import('../../src/shared/api');
    vi.mocked(client.stats.activityHeatmap).mockResolvedValue(MOCK_HEATMAP_DATA);
  });

  test('shows loading placeholder initially', () => {
    render(<ActivityHeatmap />);
    expect(screen.getByText(t('dashboard.chart.loading_activity'))).toBeDefined();
  });

  test('renders heatmap grid after data loads', async () => {
    const { container } = render(<ActivityHeatmap />);
    await waitFor(() => {
      expect(container.querySelector('.heatmap-wrapper')).not.toBeNull();
    });
    expect(container.querySelector('.heatmap-grid')).not.toBeNull();
    expect(container.querySelector('.heatmap-legend')).not.toBeNull();
  });

  test('renders day-of-week labels', async () => {
    const { container } = render(<ActivityHeatmap />);
    await waitFor(() => {
      expect(container.querySelector('.heatmap-days-labels')).not.toBeNull();
    });
    const labels = container.querySelectorAll('.heatmap-days-labels span');
    expect(labels.length).toBe(3);
  });

  test('renders summary with attempt counts', async () => {
    const { container } = render(<ActivityHeatmap />);
    await waitFor(() => {
      expect(container.querySelector('.heatmap-summary')).not.toBeNull();
    });
    expect(container.querySelector('.heatmap-total')).not.toBeNull();
    expect(container.querySelector('.heatmap-days')).not.toBeNull();
  });

  test('handles API error gracefully', async () => {
    const { client } = await import('../../src/shared/api');
    vi.mocked(client.stats.activityHeatmap).mockRejectedValue(new Error('Network error'));

    render(<ActivityHeatmap />);
    await waitFor(() => {
      expect(screen.getByText(t('heatmap.error'))).toBeDefined();
    });
  });
});
