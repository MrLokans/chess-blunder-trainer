import { describe, it, expect, vi } from 'vitest';

vi.stubGlobal('t', (key: string, params?: Record<string, unknown>) => {
  if (params) return `${key}:${JSON.stringify(params)}`;
  return key;
});

import {
  renderPhaseBreakdown, renderColorBreakdown, renderGameTypeBreakdown,
  renderDifficultyBreakdown, renderCollapsePoint, renderConversionResilience,
  renderTrapsSummary, renderGameBreakdown,
} from '../../src/dashboard/renderers';

describe('renderPhaseBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderPhaseBreakdown({ total_blunders: 0, by_phase: [] });
    expect(result.showBar).toBe(false);
    expect(result.cards).toContain('no_phase_data');
  });

  it('returns bar and cards for valid data', () => {
    const result = renderPhaseBreakdown({
      total_blunders: 10,
      by_phase: [
        { phase: 'opening', count: 3, percentage: 30, avg_cp_loss: 150 },
        { phase: 'middlegame', count: 7, percentage: 70, avg_cp_loss: 200 },
      ],
    });
    expect(result.showBar).toBe(true);
    expect(result.bar).toContain('phase-bar-segment');
    expect(result.cards).toContain('phase-card');
  });
});

describe('renderColorBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderColorBreakdown({ total_blunders: 0, by_color: [] });
    expect(result.showBar).toBe(false);
  });

  it('renders cards for valid data', () => {
    const result = renderColorBreakdown({
      total_blunders: 5,
      by_color: [{ color: 'white', count: 3, percentage: 60, avg_cp_loss: 100 }],
    });
    expect(result.showBar).toBe(true);
    expect(result.cards).toContain('color-card');
  });
});

describe('renderGameTypeBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderGameTypeBreakdown({ total_blunders: 0, by_game_type: [] });
    expect(result.showBar).toBe(false);
  });

  it('renders legend and cards', () => {
    const result = renderGameTypeBreakdown({
      total_blunders: 10,
      by_game_type: [
        { game_type: 'blitz', count: 7, percentage: 70 },
        { game_type: 'rapid', count: 3, percentage: 30 },
      ],
    });
    expect(result.showBar).toBe(true);
    expect(result.legend).toContain('game-type-legend-item');
    expect(result.cards).toContain('game-type-card');
  });
});

describe('renderDifficultyBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderDifficultyBreakdown({ total_blunders: 0, by_difficulty: [] });
    expect(result.showBar).toBe(false);
  });

  it('renders cards with correct classes', () => {
    const result = renderDifficultyBreakdown({
      total_blunders: 5,
      by_difficulty: [
        { difficulty: 'easy', count: 3, percentage: 60, avg_cp_loss: 100 },
        { difficulty: 'hard', count: 2, percentage: 40, avg_cp_loss: 300 },
      ],
    });
    expect(result.cards).toContain('diff-easy');
    expect(result.cards).toContain('diff-hard');
  });
});

describe('renderCollapsePoint', () => {
  it('returns empty state when no collapse data', () => {
    const html = renderCollapsePoint({
      avg_collapse_move: null, median_collapse_move: null,
      total_games_with_blunders: 0, total_games_without_blunders: 0,
      distribution: [],
    });
    expect(html).toContain('collapse.no_data');
  });

  it('renders distribution bars for valid data', () => {
    const html = renderCollapsePoint({
      avg_collapse_move: 15,
      median_collapse_move: 14,
      total_games_with_blunders: 10,
      total_games_without_blunders: 5,
      distribution: [
        { move_range: '1-5', count: 2 },
        { move_range: '6-10', count: 3 },
        { move_range: '11-15', count: 5 },
      ],
    });
    expect(html).toContain('collapse-bar-row');
    expect(html).toContain('collapse-big-number');
  });
});

describe('renderConversionResilience', () => {
  it('returns empty state for no data', () => {
    const html = renderConversionResilience({
      games_with_advantage: 0, games_converted: 0, conversion_rate: 0,
      games_with_disadvantage: 0, games_saved: 0, resilience_rate: 0,
    });
    expect(html).toContain('conversion.no_data');
  });

  it('renders metrics for valid data', () => {
    const html = renderConversionResilience({
      games_with_advantage: 10, games_converted: 7, conversion_rate: 70,
      games_with_disadvantage: 5, games_saved: 1, resilience_rate: 20,
    });
    expect(html).toContain('cr-metric-card');
    expect(html).toContain('70%');
    expect(html).toContain('20%');
  });
});

describe('renderTrapsSummary', () => {
  it('returns empty state for no traps data', () => {
    const html = renderTrapsSummary({ summary: { total_sprung: 0, total_entered: 0 }, stats: [] });
    expect(html).toContain('traps.no_data');
  });

  it('renders summary with counts', () => {
    const html = renderTrapsSummary({
      summary: { total_sprung: 3, total_entered: 5, top_traps: [{ trap_id: 'stafford', count: 2 }] },
      stats: [{ trap_id: 'stafford', name: 'Stafford Gambit' }],
    });
    expect(html).toContain('3');
    expect(html).toContain('5');
    expect(html).toContain('Stafford Gambit');
  });
});

describe('renderGameBreakdown', () => {
  it('renders table rows', () => {
    const html = renderGameBreakdown([
      { source: 'lichess', username: 'user1', total_games: 100, analyzed_games: 80, pending_games: 20 },
    ]);
    expect(html).toContain('lichess');
    expect(html).toContain('user1');
    expect(html).toContain('100');
  });

  it('returns empty string for empty items', () => {
    const html = renderGameBreakdown([]);
    expect(html).toBe('');
  });
});
