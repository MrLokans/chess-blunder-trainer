import { describe, test, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import {
  PhaseBreakdown,
  GameTypeBreakdown,
  CollapsePointBreakdown,
  EcoBreakdown,
  GameBreakdownTable,
  ConversionResilienceBreakdown,
} from '../../src/dashboard/breakdowns';

describe('PhaseBreakdown', () => {
  test('shows no_data when empty', () => {
    render(<PhaseBreakdown data={{ total_blunders: 0, by_phase: [] }} />);
    expect(screen.getByText('dashboard.chart.no_phase_data')).toBeDefined();
  });

  test('renders phase cards with percentages', () => {
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
    expect(container.querySelectorAll('.phase-card').length).toBe(2);
    expect(container.querySelector('.phase-card.opening')).toBeDefined();
    expect(container.querySelector('.phase-card.middlegame')).toBeDefined();
  });

  test('renders bar segments for non-zero percentages', () => {
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
    expect(container.querySelectorAll('.phase-bar-segment').length).toBe(2);
  });
});

describe('GameTypeBreakdown', () => {
  test('shows no_data when empty', () => {
    render(<GameTypeBreakdown data={{ total_blunders: 0, by_game_type: [] }} />);
    expect(screen.getByText('dashboard.chart.no_game_type_data')).toBeDefined();
  });

  test('renders bar segments', () => {
    const { container } = render(
      <GameTypeBreakdown
        data={{
          total_blunders: 10,
          by_game_type: [
            { game_type: 'blitz', count: 7, percentage: 70 },
            { game_type: 'rapid', count: 3, percentage: 30 },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.game-type-bar-segment').length).toBe(2);
  });

  test('renders legend items', () => {
    const { container } = render(
      <GameTypeBreakdown
        data={{
          total_blunders: 10,
          by_game_type: [
            { game_type: 'blitz', count: 7, percentage: 70 },
            { game_type: 'rapid', count: 3, percentage: 30 },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.game-type-legend-item').length).toBe(2);
  });

  test('renders game type cards for non-zero counts', () => {
    const { container } = render(
      <GameTypeBreakdown
        data={{
          total_blunders: 10,
          by_game_type: [
            { game_type: 'blitz', count: 7, percentage: 70 },
            { game_type: 'rapid', count: 0, percentage: 0 },
          ],
        }}
      />
    );
    expect(container.querySelectorAll('.game-type-card').length).toBe(1);
    expect(container.querySelector('.game-type-card.blitz')).toBeDefined();
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
    expect(container.querySelectorAll('.collapse-bar-row').length).toBe(3);
    expect(container.querySelector('.collapse-big-number')).toBeDefined();
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
    expect(container.querySelectorAll('.collapse-zone-item').length).toBe(3);
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
    expect(container.querySelector('.eco-group-header')).toBeDefined();
    expect(container.querySelectorAll('.eco-group-child').length).toBe(2);
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

    const childRows = container.querySelectorAll<HTMLElement>('.eco-group-child');
    expect(childRows[0]!.style.display).toBe('none');

    const header = container.querySelector('.eco-group-header') as HTMLElement;
    fireEvent.click(header);

    const childRowsAfter = container.querySelectorAll<HTMLElement>('.eco-group-child');
    expect(childRowsAfter[0]!.style.display).not.toBe('none');

    fireEvent.click(header);
    const childRowsCollapsed = container.querySelectorAll<HTMLElement>('.eco-group-child');
    expect(childRowsCollapsed[0]!.style.display).toBe('none');
  });
});

describe('GameBreakdownTable', () => {
  test('renders table rows with correct data', () => {
    const { container } = render(
      <table>
        <tbody>
          <GameBreakdownTable
            items={[
              { source: 'lichess', username: 'user1', total_games: 100, analyzed_games: 80, pending_games: 20 },
            ]}
          />
        </tbody>
      </table>
    );
    expect(screen.getByText('lichess')).toBeDefined();
    expect(screen.getByText('user1')).toBeDefined();
    expect(screen.getByText('100')).toBeDefined();
    expect(screen.getByText('80')).toBeDefined();
    expect(screen.getByText('20')).toBeDefined();
    expect(container.querySelectorAll('tr').length).toBe(1);
  });

  test('renders no_data message for empty items', () => {
    render(<GameBreakdownTable items={[]} />);
    expect(screen.getByText('dashboard.no_data')).toBeDefined();
  });

  test('renders multiple rows', () => {
    const { container } = render(
      <table>
        <tbody>
          <GameBreakdownTable
            items={[
              { source: 'lichess', username: 'user1', total_games: 50, analyzed_games: 40, pending_games: 10 },
              { source: 'chess.com', username: 'user2', total_games: 30, analyzed_games: 25, pending_games: 5 },
            ]}
          />
        </tbody>
      </table>
    );
    expect(container.querySelectorAll('tr').length).toBe(2);
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
    expect(container.querySelectorAll('.cr-metric-card').length).toBe(2);
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
    expect(container.querySelectorAll('.cr-metric-card').length).toBe(2);
  });
});
