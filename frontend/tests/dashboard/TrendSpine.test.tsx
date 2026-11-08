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

const LOWER = { lowerIsBetter: true, noise: 0.1 };
const HIGHER = { lowerIsBetter: false, noise: 2 };

describe('compareEnds', () => {
  test('averages up to three blocks at each end', () => {
    expect(compareEnds([1, 2, 3, 9, 4, 5, 6], LOWER)).toEqual({ before: 2, now: 5, blocks: 3, direction: 'declining' });
  });

  test('uses one block per end when only two or three exist', () => {
    expect(compareEnds([3, 2], LOWER)).toMatchObject({ before: 3, now: 2, blocks: 1, direction: 'improving' });
    expect(compareEnds([3, 9, 2], LOWER)).toMatchObject({ before: 3, now: 2, blocks: 1 });
  });

  test('reads a rise as improving when higher is better', () => {
    expect(compareEnds([10, 30], HIGHER)?.direction).toBe('improving');
  });

  test('calls moves inside the noise floor stable, even from a small start', () => {
    expect(compareEnds([0.8, 0.88], LOWER)?.direction).toBe('stable');
    expect(compareEnds([0.8, 0.95], LOWER)?.direction).toBe('declining');
  });

  test('calls moves inside 5% of a large start stable', () => {
    expect(compareEnds([500, 520], { lowerIsBetter: true, noise: 10 })?.direction).toBe('stable');
  });

  test('skips blocks without a value instead of reading them as zero', () => {
    expect(compareEnds([30, null, 20, 40, null, 40], { lowerIsBetter: true, noise: 2 })).toMatchObject({ before: 25, now: 40, direction: 'declining' });
    expect(compareEnds([null, 30], { lowerIsBetter: true, noise: 2 })).toBeNull();
  });

  test('needs two blocks', () => {
    expect(compareEnds([2], LOWER)).toBeNull();
  });
});

describe('niceScale', () => {
  test('rounds the top up to a whole step', () => {
    expect(niceScale(4.25)).toEqual({ top: 5, step: 1 });
    expect(niceScale(37)).toEqual({ top: 40, step: 10 });
  });

  test('keeps small fractional maxima readable', () => {
    expect(niceScale(0.03)).toEqual({ top: 0.03, step: 0.01 });
  });

  test('handles an all-zero series', () => {
    expect(niceScale(0).top).toBeGreaterThan(0);
  });
});

describe('TrendSpine', () => {
  test('labels the compared games by their real ranges when the oldest games fall outside the blocks', () => {
    const growth = makeGrowth([2, 2, 3, 3]);
    growth.windows = growth.windows.map(w => ({ ...w, game_start: w.game_start + 15, game_end: w.game_end + 15 }));
    render(<TrendSpine growth={growth} nextStep={null} />);
    expect(screen.getAllByText(t('dashboard.trend.compare_ranges', { firstStart: 16, firstEnd: 55, lastStart: 56, lastEnd: 95 })).length).toBeGreaterThan(0);
  });

  test('states the verdict and compares first and last blocks', () => {
    render(<TrendSpine growth={makeGrowth([2, 2, 2, 3, 3, 3])} nextStep={null} />);
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(t('dashboard.trend.verdict.declining'));
    expect(screen.getAllByText(t('dashboard.trend.compare_ranges', { firstStart: 1, firstEnd: 60, lastStart: 61, lastEnd: 120 })).length).toBeGreaterThan(0);
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

  test('leaves a gap for a block without blunders when showing loss per blunder', () => {
    const growth = makeGrowth([2, 2, 2, 2]);
    growth.windows = growth.windows.map((w, i) => (i === 1 ? { ...w, avg_blunder_severity: null } : w));
    const { container } = render(<TrendSpine growth={growth} nextStep={null} />);
    fireEvent.click(screen.getByTestId('tab-avg_blunder_severity'));
    expect(container.querySelectorAll('.trend-chart__bar--empty')).toHaveLength(1);
    expect(container.querySelectorAll('.trend-chart table tbody tr')).toHaveLength(4);
  });

  test('asks for more games with a single block and still shows the next step', () => {
    render(<TrendSpine growth={makeGrowth([2])} nextStep={<p>next</p>} />);
    expect(screen.getByText(t('growth.insufficient_data', { count: 40 }))).toBeDefined();
    expect(screen.getByText('next')).toBeDefined();
  });
});
