import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { FiltersPanel } from '../../src/trainer/components/FiltersPanel';
import type { FiltersAPI } from '../../src/trainer/hooks/useFilters';

function makeFilters(overrides?: Partial<FiltersAPI>): FiltersAPI {
  return {
    state: {
      phases: ['opening', 'middlegame', 'endgame'],
      gameTypes: ['bullet', 'blitz', 'rapid', 'classical'],
      difficulties: ['easy', 'medium', 'hard'],
      tacticalPattern: null,
      color: 'both',
      playFullLine: false,
      showCoordinates: true,
      showArrows: true,
      showThreats: false,
      showTactics: true,
      filtersCollapsed: false,
      boardSettingsCollapsed: false,
    },
    getFilterParams: vi.fn(() => ({})),
    hasActiveFilters: vi.fn(() => false),
    activeFilterCount: vi.fn(() => 0),
    clearAllFilters: vi.fn(),
    setPhases: vi.fn(),
    setGameTypes: vi.fn(),
    setDifficulties: vi.fn(),
    setTacticalPattern: vi.fn(),
    setColor: vi.fn(),
    setPlayFullLine: vi.fn(),
    setShowCoordinates: vi.fn(),
    setShowArrows: vi.fn(),
    setShowThreats: vi.fn(),
    setShowTactics: vi.fn(),
    toggleFiltersCollapsed: vi.fn(),
    toggleBoardSettingsCollapsed: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  window.__features = { 'trainer.tactics': true };
});

describe('FiltersPanel', () => {
  it('renders filter groups when not collapsed', () => {
    const filters = makeFilters();
    render(<FiltersPanel filters={filters} />);
    expect(screen.getByText('trainer.filters.game_type')).not.toBeNull();
    expect(screen.getByText('trainer.filters.phase')).not.toBeNull();
    expect(screen.getByText('trainer.filters.difficulty')).not.toBeNull();
  });

  it('hides content when collapsed', () => {
    const filters = makeFilters({
      state: { ...makeFilters().state, filtersCollapsed: true },
    });
    render(<FiltersPanel filters={filters} />);
    expect(screen.queryByText('trainer.filters.game_type')).toBeNull();
  });

  it('calls toggle on header click', () => {
    const filters = makeFilters();
    render(<FiltersPanel filters={filters} />);
    fireEvent.click(screen.getByText('trainer.filters.title'));
    expect(filters.toggleFiltersCollapsed).toHaveBeenCalled();
  });

  it('shows active filter count badge', () => {
    const filters = makeFilters({ activeFilterCount: vi.fn(() => 3) });
    const { container } = render(<FiltersPanel filters={filters} />);
    const badge = container.querySelector('.filters-count-badge');
    expect(badge).not.toBeNull();
    expect((badge as HTMLElement).textContent).toBe('3 active');
  });
});
