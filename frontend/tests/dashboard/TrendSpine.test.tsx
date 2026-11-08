import { describe, test, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { TrendSpine, compareEnds, niceScale } from '../../src/dashboard/TrendSpine';
import type { GrowthData } from '../../src/dashboard/types';

function makeGrowth(bpg: number[], clean: number[] = bpg.map(() => 20)): GrowthData {
  return {
    total_games: bpg.length * 20,
    window_size: 20,
    windows: bpg.map((v, i) => ({
      window_index: i,
      game_start: i * 20 + 1,
      game_end: i * 20 + 20,
      avg_blunders_per_game: v,
      avg_cpl: 80,
      avg_blunder_severity: 500,
      clean_game_rate: clean[i] ?? 0,
      catastrophic_rate: 30,
    })),
  };
}

describe('compareEnds', () => {
  test('averages up to three blocks at each end', () => {
    expect(compareEnds([1, 2, 3, 9, 4, 5, 6], true)).toEqual({ before: 2, now: 5, blocks: 3, direction: 'declining' });
  });

  test('uses one block per end when only two exist', () => {
    expect(compareEnds([3, 2], true)).toMatchObject({ before: 3, now: 2, blocks: 1, direction: 'improving' });
  });

  test('reads a rise as improving when higher is better', () => {
    expect(compareEnds([10, 30], false)?.direction).toBe('improving');
  });

  test('calls small moves stable', () => {
    expect(compareEnds([2, 2.08], true)?.direction).toBe('stable');
  });

  test('measures moves from a zero start in absolute units', () => {
    expect(compareEnds([0, 0.5], false)?.direction).toBe('improving');
  });

  test('needs two blocks', () => {
    expect(compareEnds([2], true)).toBeNull();
  });
});

describe('niceScale', () => {
  test('rounds the top up to a whole step', () => {
    expect(niceScale(4.25)).toEqual({ top: 5, step: 1 });
    expect(niceScale(37)).toEqual({ top: 40, step: 10 });
  });

  test('handles an all-zero series', () => {
    expect(niceScale(0).top).toBeGreaterThan(0);
  });
});

describe('TrendSpine', () => {
  test('states the verdict and compares first and last blocks', () => {
    render(<TrendSpine growth={makeGrowth([2, 2, 2, 3, 3, 3])} nextStep={null} />);
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(t('dashboard.trend.verdict.declining'));
    expect(screen.getAllByText(t('dashboard.trend.compare', { count: 60 })).length).toBeGreaterThan(0);
  });

  test('switching the metric tab redraws the verdict for that metric', () => {
    render(<TrendSpine growth={makeGrowth([2, 2, 2, 3, 3, 3], [10, 10, 10, 30, 30, 30])} nextStep={null} />);
    fireEvent.click(screen.getByTestId('tab-clean_game_rate'));
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(t('dashboard.trend.verdict.improving'));
    expect(document.querySelector('[data-metric="clean_game_rate"]')).toBeNull();
    expect(document.querySelector('[data-metric="avg_blunders_per_game"]')).not.toBeNull();
  });

  test('draws one bar per block and marks the compared ends', () => {
    const { container } = render(<TrendSpine growth={makeGrowth([1, 2, 3, 4, 5, 6, 7])} nextStep={null} />);
    expect(container.querySelectorAll('.trend-chart__bar')).toHaveLength(7);
    expect(container.querySelectorAll('.trend-chart__bar--first')).toHaveLength(3);
    expect(container.querySelectorAll('.trend-chart__bar--last')).toHaveLength(3);
  });

  test('asks for more games with a single block and still shows the next step', () => {
    render(<TrendSpine growth={makeGrowth([2])} nextStep={<p>next</p>} />);
    expect(screen.getByText(t('growth.insufficient_data', { count: 40 }))).toBeDefined();
    expect(screen.getByText('next')).toBeDefined();
  });
});
