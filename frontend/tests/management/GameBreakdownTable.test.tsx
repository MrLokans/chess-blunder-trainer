import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { GameBreakdownTable } from '../../src/management/GameBreakdownTable';

describe('GameBreakdownTable', () => {
  test('renders table rows with correct data', () => {
    const { container } = render(
      <GameBreakdownTable
        items={[
          { source: 'lichess', username: 'user1', total_games: 100, analyzed_games: 80, pending_games: 20 },
        ]}
      />
    );
    expect(screen.getByText('lichess')).toBeDefined();
    expect(screen.getByText('user1')).toBeDefined();
    expect(screen.getByText('100')).toBeDefined();
    expect(screen.getByText('80')).toBeDefined();
    expect(screen.getByText('20')).toBeDefined();
    expect(container.querySelectorAll('tbody tr').length).toBe(1);
  });

  test('renders no_data message for empty items', () => {
    render(<GameBreakdownTable items={[]} />);
    expect(screen.getByText('dashboard.no_data')).toBeDefined();
  });

  test('renders multiple rows', () => {
    const { container } = render(
      <GameBreakdownTable
        items={[
          { source: 'lichess', username: 'user1', total_games: 50, analyzed_games: 40, pending_games: 10 },
          { source: 'chess.com', username: 'user2', total_games: 30, analyzed_games: 25, pending_games: 5 },
        ]}
      />
    );
    expect(container.querySelectorAll('tbody tr').length).toBe(2);
  });
});
