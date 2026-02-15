import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

// Provide t() globally for renderer functions
globalThis.t = (key, params) => {
  if (params) return `${key}:${JSON.stringify(params)}`;
  return key;
};

const {
  renderPhaseBreakdown, renderColorBreakdown, renderGameTypeBreakdown,
  renderDifficultyBreakdown, renderCollapsePoint, renderConversionResilience,
  renderTrapsSummary, renderGameBreakdown,
} = await import('../blunder_tutor/web/static/js/dashboard/renderers.js');

describe('renderPhaseBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderPhaseBreakdown({ total_blunders: 0, by_phase: [] });
    assert.equal(result.showBar, false);
    assert.ok(result.cards.includes('no_phase_data'));
  });

  it('returns bar and cards for valid data', () => {
    const result = renderPhaseBreakdown({
      total_blunders: 10,
      by_phase: [
        { phase: 'opening', count: 3, percentage: 30, avg_cp_loss: 150 },
        { phase: 'middlegame', count: 7, percentage: 70, avg_cp_loss: 200 },
      ],
    });
    assert.equal(result.showBar, true);
    assert.ok(result.bar.includes('phase-bar-segment'));
    assert.ok(result.cards.includes('phase-card'));
  });
});

describe('renderColorBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderColorBreakdown({ total_blunders: 0, by_color: [] });
    assert.equal(result.showBar, false);
  });

  it('renders cards for valid data', () => {
    const result = renderColorBreakdown({
      total_blunders: 5,
      by_color: [{ color: 'white', count: 3, percentage: 60, avg_cp_loss: 100 }],
    });
    assert.equal(result.showBar, true);
    assert.ok(result.cards.includes('color-card'));
  });
});

describe('renderGameTypeBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderGameTypeBreakdown({ total_blunders: 0, by_game_type: [] });
    assert.equal(result.showBar, false);
  });

  it('renders legend and cards', () => {
    const result = renderGameTypeBreakdown({
      total_blunders: 10,
      by_game_type: [
        { game_type: 'blitz', count: 7, percentage: 70 },
        { game_type: 'rapid', count: 3, percentage: 30 },
      ],
    });
    assert.equal(result.showBar, true);
    assert.ok(result.legend.includes('game-type-legend-item'));
    assert.ok(result.cards.includes('game-type-card'));
  });
});

describe('renderDifficultyBreakdown', () => {
  it('returns empty state for no data', () => {
    const result = renderDifficultyBreakdown({ total_blunders: 0, by_difficulty: [] });
    assert.equal(result.showBar, false);
  });

  it('renders cards with correct classes', () => {
    const result = renderDifficultyBreakdown({
      total_blunders: 5,
      by_difficulty: [
        { difficulty: 'easy', count: 3, percentage: 60, avg_cp_loss: 100 },
        { difficulty: 'hard', count: 2, percentage: 40, avg_cp_loss: 300 },
      ],
    });
    assert.ok(result.cards.includes('diff-easy'));
    assert.ok(result.cards.includes('diff-hard'));
  });
});

describe('renderCollapsePoint', () => {
  it('returns empty state when no collapse data', () => {
    const html = renderCollapsePoint({ avg_collapse_move: null, total_games_with_blunders: 0 });
    assert.ok(html.includes('collapse.no_data'));
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
    assert.ok(html.includes('collapse-bar-row'));
    assert.ok(html.includes('collapse-big-number'));
  });
});

describe('renderConversionResilience', () => {
  it('returns empty state for no data', () => {
    const html = renderConversionResilience({ games_with_advantage: 0, games_with_disadvantage: 0 });
    assert.ok(html.includes('conversion.no_data'));
  });

  it('renders metrics for valid data', () => {
    const html = renderConversionResilience({
      games_with_advantage: 10, games_converted: 7, conversion_rate: 70,
      games_with_disadvantage: 5, games_saved: 1, resilience_rate: 20,
    });
    assert.ok(html.includes('cr-metric-card'));
    assert.ok(html.includes('70%'));
    assert.ok(html.includes('20%'));
  });
});

describe('renderTrapsSummary', () => {
  it('returns empty state for no traps data', () => {
    const html = renderTrapsSummary({ summary: { total_sprung: 0, total_entered: 0 }, stats: [] });
    assert.ok(html.includes('traps.no_data'));
  });

  it('renders summary with counts', () => {
    const html = renderTrapsSummary({
      summary: { total_sprung: 3, total_entered: 5, top_traps: [{ trap_id: 'stafford', count: 2 }] },
      stats: [{ trap_id: 'stafford', name: 'Stafford Gambit' }],
    });
    assert.ok(html.includes('3'));
    assert.ok(html.includes('5'));
    assert.ok(html.includes('Stafford Gambit'));
  });
});

describe('renderGameBreakdown', () => {
  it('renders table rows', () => {
    const html = renderGameBreakdown([
      { source: 'lichess', username: 'user1', total_games: 100, analyzed_games: 80, pending_games: 20 },
    ]);
    assert.ok(html.includes('lichess'));
    assert.ok(html.includes('user1'));
    assert.ok(html.includes('100'));
  });

  it('returns empty string for empty items', () => {
    const html = renderGameBreakdown([]);
    assert.equal(html, '');
  });
});
