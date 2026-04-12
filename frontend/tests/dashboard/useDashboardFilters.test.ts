import { describe, test, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useDashboardFilters } from '../../src/dashboard/useDashboardFilters';

describe('useDashboardFilters', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('returns default filter state', () => {
    const { result } = renderHook(() => useDashboardFilters());
    expect(result.current.datePreset).toBe('all');
    expect(result.current.dateFrom).toBeNull();
    expect(result.current.dateTo).toBeNull();
    expect(result.current.gameTypes).toEqual(['bullet', 'blitz', 'rapid', 'classical']);
    expect(result.current.gamePhases).toEqual(['opening', 'middlegame', 'endgame']);
  });

  test('setDatePreset updates date range', async () => {
    const { result } = renderHook(() => useDashboardFilters());
    await act(() => { result.current.setDatePreset('7d'); });
    expect(result.current.datePreset).toBe('7d');
    expect(result.current.dateFrom).not.toBeNull();
    expect(result.current.dateTo).not.toBeNull();
  });

  test('setCustomDateRange clears preset', async () => {
    const { result } = renderHook(() => useDashboardFilters());
    await act(() => { result.current.setCustomDateRange('2024-01-01', '2024-06-01'); });
    expect(result.current.datePreset).toBeNull();
    expect(result.current.dateFrom).toBe('2024-01-01');
    expect(result.current.dateTo).toBe('2024-06-01');
  });

  test('setGameTypes updates and persists', async () => {
    const { result } = renderHook(() => useDashboardFilters());
    await act(() => { result.current.setGameTypes(['blitz', 'rapid']); });
    expect(result.current.gameTypes).toEqual(['blitz', 'rapid']);
    const stored = localStorage.getItem('dashboard-game-type-filters');
    expect(JSON.parse(stored ?? '[]')).toEqual(['blitz', 'rapid']);
  });

  test('getParams omits game_types when all selected', () => {
    const { result } = renderHook(() => useDashboardFilters());
    const params = result.current.getParams();
    expect(params.game_types).toBeUndefined();
    expect(params.game_phases).toBeUndefined();
  });

  test('getParams includes game_types when subset selected', async () => {
    const { result } = renderHook(() => useDashboardFilters());
    await act(() => { result.current.setGameTypes(['blitz']); });
    const params = result.current.getParams();
    expect(params.game_types).toEqual(['blitz']);
  });

  test('getParams includes date range from preset', async () => {
    const { result } = renderHook(() => useDashboardFilters());
    await act(() => { result.current.setDatePreset('30d'); });
    const params = result.current.getParams();
    expect(params.start_date).toBeDefined();
    expect(params.end_date).toBeDefined();
  });

  test('restores state from localStorage', () => {
    localStorage.setItem('dashboard-game-type-filters', JSON.stringify(['rapid']));
    localStorage.setItem('dashboard-game-phase-filters', JSON.stringify(['endgame']));
    localStorage.setItem('dashboard-date-filter', JSON.stringify({ type: 'preset', preset: '7d' }));

    const { result } = renderHook(() => useDashboardFilters());
    expect(result.current.gameTypes).toEqual(['rapid']);
    expect(result.current.gamePhases).toEqual(['endgame']);
    expect(result.current.datePreset).toBe('7d');
  });
});
