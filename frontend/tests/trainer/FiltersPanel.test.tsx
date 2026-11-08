import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { FiltersPanel, FilterSummary } from '../../src/trainer/components/FiltersPanel';
import type { FiltersAPI } from '../../src/trainer/hooks/useFilters';

function makeFilters(overrides?: Partial<FiltersAPI>): FiltersAPI {
  return {
    state: {
      phases: ['opening', 'middlegame', 'endgame'],
      gameTypes: ['bullet', 'blitz', 'rapid', 'classical'],
      difficulties: ['easy', 'medium', 'hard'],
      tacticalPattern: null,
      color: 'both',
      showCoordinates: true,
      showArrows: true,
      showThreats: false,
      showTactics: true,
    },
    getFilterParams: vi.fn(() => ({})),
    clearAllFilters: vi.fn(),
    setPhases: vi.fn(),
    setGameTypes: vi.fn(),
    setDifficulties: vi.fn(),
    setTacticalPattern: vi.fn(),
    setColor: vi.fn(),
    setShowArrows: vi.fn(),
    setShowThreats: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  window.__features = { 'trainer.tactics': true };
});

describe('FiltersPanel', () => {
  it('renders filter groups for the drawer', () => {
    const filters = makeFilters();
    render(<FiltersPanel filters={filters} />);
    expect(screen.getByText('trainer.filters.game_type')).not.toBeNull();
    expect(screen.getByText('trainer.filters.phase')).not.toBeNull();
    expect(screen.getByText('trainer.filters.difficulty')).not.toBeNull();
  });
});

describe('FilterSummary', () => {
  it('says all puzzles when nothing is narrowed', () => {
    render(<FilterSummary filters={makeFilters()} onChange={vi.fn()} />);
    expect(screen.getByTestId('filter-summary').textContent).toBe('trainer.filters.all_puzzles');
  });

  it('lists only the narrowed filters', () => {
    const base = makeFilters().state;
    const filters = makeFilters({ state: { ...base, gameTypes: ['blitz', 'rapid'], tacticalPattern: 'hanging_piece', color: 'black' } });
    render(<FilterSummary filters={filters} onChange={vi.fn()} />);
    expect(screen.getByTestId('filter-summary').textContent).toBe(
      'trainer.game_type.blitz, trainer.game_type.rapid · trainer.filters.tactical_hanging · chess.color.black',
    );
  });

  it('opens the drawer from the change button', () => {
    const onChange = vi.fn();
    render(<FilterSummary filters={makeFilters()} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('change-filters'));
    expect(onChange).toHaveBeenCalled();
  });
});
