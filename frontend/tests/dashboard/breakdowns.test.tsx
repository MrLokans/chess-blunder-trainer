import { describe, test, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import {
  PhaseBreakdown,
  TacticalBreakdown,
  GameTypeBreakdown,
  CollapsePointBreakdown,
  EcoBreakdown,
  ConversionResilienceBreakdown,
} from '../../src/dashboard/breakdowns';

describe('PhaseBreakdown', () => {
  test('shows no_data when empty', () => {
    render(<PhaseBreakdown data={{ total_blunders: 0, by_phase: [] }} />);
    expect(screen.getByText('dashboard.chart.no_phase_data')).toBeDefined();
  });

  test('draws one ranked row per phase and marks the largest', () => {
    const { container } = render(
      <PhaseBreakdown
        data={{
          total_blunders: 10,
          by_phase: [
            { phase: 'opening', count: 3, percentage: 30, avg_cp_loss: 150 },
            { phase: 'middlegame', count: 7, percentage: 70, avg_cp_loss: 200 },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.ranked-bars tbody tr')).toHaveLength(2);
    expect(container.querySelector('.ranked-bars__row--top')?.getAttribute('data-key')).toBe('middlegame');
    expect(screen.getByText('70%')).toBeDefined();
  });

});

describe('TacticalBreakdown', () => {
  test('ranks named patterns first and never singles out the unclassified bucket', () => {
    const { container } = render(
      <TacticalBreakdown
        data={{
          total_blunders: 10,
          by_pattern: [
            { pattern: 'None', count: 6, percentage: 60, avg_cp_loss: 300 },
            { pattern: 'Fork', count: 1, percentage: 10, avg_cp_loss: 300 },
            { pattern: 'Trapped Piece', count: 3, percentage: 30, avg_cp_loss: 300 },
          ],
        }}
      />
    );

    const keys = Array.from(container.querySelectorAll('.ranked-bars tbody tr')).map(row => row.getAttribute('data-key'));
    expect(keys).toEqual(['Trapped Piece', 'Fork', 'None']);
    expect(container.querySelector('.ranked-bars__row--top')?.getAttribute('data-key')).toBe('Trapped Piece');
    expect(container.querySelector('.ranked-bars__row--muted')?.getAttribute('data-key')).toBe('None');
    expect(screen.getByText(t('dashboard.tactical.trapped'))).toBeDefined();
  });
});

describe('GameTypeBreakdown', () => {
  test('shows no_data when empty', () => {
    render(<GameTypeBreakdown data={{ total_blunders: 0, by_game_type: [] }} />);
    expect(screen.getByText('dashboard.chart.no_game_type_data')).toBeDefined();
  });

  test('ranks played time controls by blunders per game', () => {
    const { container } = render(
      <GameTypeBreakdown
        data={{
          total_blunders: 10,
          by_game_type: [
            { game_type: 'blitz', count: 7, percentage: 70, game_count: 5, blunders_per_game: 1.4 },
            { game_type: 'rapid', count: 3, percentage: 30, game_count: 6, blunders_per_game: 0.5 },
            { game_type: 'classical', count: 0, percentage: 0, game_count: 0, blunders_per_game: null },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.ranked-bars tbody tr')).toHaveLength(2);
    expect(container.querySelector('.ranked-bars__row--top')?.getAttribute('data-key')).toBe('blitz');
  });
});

describe('CollapsePointBreakdown', () => {
  test('shows no_data when avg_collapse_move is null', () => {
    render(
      <CollapsePointBreakdown
        data={{
          avg_collapse_move: null,
          median_collapse_move: null,
          total_games_with_blunders: 0,
          total_games_without_blunders: 0,
          distribution: [],
        }}
      />
    );
    expect(screen.getByText('dashboard.collapse.no_data')).toBeDefined();
  });

  test('renders distribution bars', () => {
    const { container } = render(
      <CollapsePointBreakdown
        data={{
          avg_collapse_move: 15,
          median_collapse_move: 14,
          total_games_with_blunders: 10,
          total_games_without_blunders: 5,
          distribution: [
            { move_range: '1-5', count: 2 },
            { move_range: '6-10', count: 3 },
            { move_range: '11-15', count: 5 },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.ranked-bars tbody tr')).toHaveLength(3);
    expect(container.querySelector('.collapse-big-number')).toBeDefined();
  });

  test('uses the median as the typical headline and labels the average', () => {
    render(
      <CollapsePointBreakdown
        data={{
          avg_collapse_move: 15,
          median_collapse_move: 14,
          total_games_with_blunders: 10,
          total_games_without_blunders: 5,
          distribution: [{ move_range: '1-5', count: 2 }],
        }}
      />
    );
    expect(screen.getByText(t('dashboard.collapse.median_move', { move: 14 }))).toBeDefined();
    expect(screen.getByText(t('dashboard.collapse.avg_move', { move: 15 }))).toBeDefined();
  });

  test('shows no_data when the median is null', () => {
    render(
      <CollapsePointBreakdown
        data={{
          avg_collapse_move: 15,
          median_collapse_move: null,
          total_games_with_blunders: 10,
          total_games_without_blunders: 5,
          distribution: [],
        }}
      />
    );
    expect(screen.getByText('dashboard.collapse.no_data')).toBeDefined();
  });

  test('renders zone legend', () => {
    const { container } = render(
      <CollapsePointBreakdown
        data={{
          avg_collapse_move: 15,
          median_collapse_move: 14,
          total_games_with_blunders: 10,
          total_games_without_blunders: 5,
          distribution: [{ move_range: '1-5', count: 2 }],
        }}
      />
    );
    expect(container.querySelectorAll('.collapse-zone-key > span')).toHaveLength(3);
  });
});

describe('EcoBreakdown', () => {
  test('shows no_data when empty', () => {
    render(<EcoBreakdown data={{ total_blunders: 0, by_opening: [] }} />);
    expect(screen.getByText('dashboard.chart.no_opening_data')).toBeDefined();
  });

  test('renders single variation as direct row', () => {
    const { container } = render(
      <EcoBreakdown
        data={{
          total_blunders: 5,
          by_opening: [
            { eco_code: 'A00', eco_name: 'Polish Opening', count: 5, percentage: 100, avg_cp_loss: 150, game_count: 3 },
          ],
        }}
      />
    );
    expect(container.querySelector('.eco-table')).toBeDefined();
    expect(container.querySelector('.eco-group-header')).toBeNull();
  });

  test('renders grouped openings with header', () => {
    const { container } = render(
      <EcoBreakdown
        data={{
          total_blunders: 10,
          by_opening: [
            { eco_code: 'B20', eco_name: 'Sicilian Defense: Open', count: 6, percentage: 60, avg_cp_loss: 120, game_count: 4 },
            { eco_code: 'B21', eco_name: 'Sicilian Defense: Closed', count: 4, percentage: 40, avg_cp_loss: 180, game_count: 3 },
          ],
        }}
      />
    );
    expect(container.querySelector('.eco-group-header')).not.toBeNull();
    expect(container.querySelector('.eco-child-indent')).toBeNull();
  });

  test('toggles expand/collapse on group header click', () => {
    const { container } = render(
      <EcoBreakdown
        data={{
          total_blunders: 10,
          by_opening: [
            { eco_code: 'B20', eco_name: 'Sicilian Defense: Open', count: 6, percentage: 60, avg_cp_loss: 120, game_count: 4 },
            { eco_code: 'B21', eco_name: 'Sicilian Defense: Closed', count: 4, percentage: 40, avg_cp_loss: 180, game_count: 3 },
          ],
        }}
      />
    );

    expect(container.querySelectorAll('.eco-child-indent').length).toBe(0);

    const header = container.querySelector('.eco-group-header') as HTMLElement;
    fireEvent.click(header);
    expect(container.querySelectorAll('.eco-child-indent').length).toBe(2);

    fireEvent.click(header);
    expect(container.querySelectorAll('.eco-child-indent').length).toBe(0);
  });
});

describe('ConversionResilienceBreakdown', () => {
  test('shows no_data when both advantages are zero', () => {
    render(
      <ConversionResilienceBreakdown
        data={{
          games_with_advantage: 0,
          games_converted: 0,
          conversion_rate: 0,
          games_with_disadvantage: 0,
          games_saved: 0,
          resilience_rate: 0,
        }}
      />
    );
    expect(screen.getByText('dashboard.conversion.no_data')).toBeDefined();
  });

  test('renders metric cards with rates', () => {
    const { container } = render(
      <ConversionResilienceBreakdown
        data={{
          games_with_advantage: 10,
          games_converted: 7,
          conversion_rate: 70,
          games_with_disadvantage: 5,
          games_saved: 1,
          resilience_rate: 20,
        }}
      />
    );
    expect(container.querySelectorAll('.ranked-bars tbody tr')).toHaveLength(2);
    expect(container.querySelector('.ranked-bars__row--top')).toBeNull();
    expect(screen.getByText('70%')).toBeDefined();
    expect(screen.getByText('20%')).toBeDefined();
  });

  test('renders when only advantage games exist', () => {
    const { container } = render(
      <ConversionResilienceBreakdown
        data={{
          games_with_advantage: 5,
          games_converted: 3,
          conversion_rate: 60,
          games_with_disadvantage: 0,
          games_saved: 0,
          resilience_rate: 0,
        }}
      />
    );
    expect(container.querySelectorAll('.ranked-bars tbody tr')).toHaveLength(2);
    expect(container.querySelector('.ranked-bars__row--top')).toBeNull();
  });
});
