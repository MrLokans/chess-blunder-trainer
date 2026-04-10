import { useState, useCallback } from 'preact/hooks';
import type { DateFilterParams, DatePreset } from './types';

const DATE_STORAGE_KEY = 'dashboard-date-filter';
const GAME_TYPE_STORAGE_KEY = 'dashboard-game-type-filters';
const GAME_PHASE_STORAGE_KEY = 'dashboard-game-phase-filters';

const ALL_GAME_TYPES = ['bullet', 'blitz', 'rapid', 'classical'];
const ALL_GAME_PHASES = ['opening', 'middlegame', 'endgame'];

interface DateState {
  preset: DatePreset | null;
  from: string | null;
  to: string | null;
}

function getPresetDates(preset: string): { from: string | null; to: string | null } {
  const now = new Date();
  const to = now.toISOString().split('T')[0] ?? '';
  const msPerDay = 24 * 60 * 60 * 1000;
  const daysMap: Record<string, number> = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 };
  const days = daysMap[preset];
  if (!days) return { from: null, to: null };
  const from = new Date(now.getTime() - days * msPerDay).toISOString().split('T')[0] ?? '';
  return { from, to };
}

function loadArray(key: string, defaults: string[]): string[] {
  const stored = localStorage.getItem(key);
  if (!stored) return defaults;
  try {
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) ? (parsed as string[]) : defaults;
  } catch {
    return defaults;
  }
}

function loadDateState(): DateState {
  try {
    const raw = localStorage.getItem(DATE_STORAGE_KEY);
    if (!raw) return { preset: 'all', from: null, to: null };
    const state = JSON.parse(raw) as { type: string; preset?: string; from?: string; to?: string };
    if (state.type === 'preset' && state.preset) {
      const dates = getPresetDates(state.preset);
      return { preset: state.preset as DatePreset, ...dates };
    }
    if (state.type === 'custom') {
      return { preset: null, from: state.from ?? null, to: state.to ?? null };
    }
  } catch { /* ignore */ }
  return { preset: 'all', from: null, to: null };
}

export interface DashboardFiltersResult {
  datePreset: DatePreset | null;
  dateFrom: string | null;
  dateTo: string | null;
  gameTypes: string[];
  gamePhases: string[];
  setDatePreset: (preset: DatePreset) => void;
  setCustomDateRange: (from: string | null, to: string | null) => void;
  clearDateFilter: () => void;
  setGameTypes: (types: string[]) => void;
  setGamePhases: (phases: string[]) => void;
  getParams: () => DateFilterParams;
}

export function useDashboardFilters(): DashboardFiltersResult {
  const [dateState, setDateState] = useState<DateState>(loadDateState);
  const [gameTypes, setGameTypesState] = useState(() => loadArray(GAME_TYPE_STORAGE_KEY, ALL_GAME_TYPES));
  const [gamePhases, setGamePhasesState] = useState(() => loadArray(GAME_PHASE_STORAGE_KEY, ALL_GAME_PHASES));

  const setDatePreset = useCallback((preset: DatePreset) => {
    const dates = getPresetDates(preset);
    setDateState({ preset, ...dates });
    localStorage.setItem(DATE_STORAGE_KEY, JSON.stringify({ type: 'preset', preset }));
  }, []);

  const setCustomDateRange = useCallback((from: string | null, to: string | null) => {
    setDateState({ preset: null, from, to });
    localStorage.setItem(DATE_STORAGE_KEY, JSON.stringify({ type: 'custom', from, to }));
  }, []);

  const clearDateFilter = useCallback(() => {
    setDateState({ preset: 'all', from: null, to: null });
    localStorage.setItem(DATE_STORAGE_KEY, JSON.stringify({ type: 'preset', preset: 'all' }));
  }, []);

  const setGameTypes = useCallback((types: string[]) => {
    setGameTypesState(types);
    localStorage.setItem(GAME_TYPE_STORAGE_KEY, JSON.stringify(types));
  }, []);

  const setGamePhases = useCallback((phases: string[]) => {
    setGamePhasesState(phases);
    localStorage.setItem(GAME_PHASE_STORAGE_KEY, JSON.stringify(phases));
  }, []);

  const getParams = useCallback((): DateFilterParams => {
    const params: DateFilterParams = {};
    if (dateState.from) params.start_date = dateState.from;
    if (dateState.to) params.end_date = dateState.to;
    if (gameTypes.length > 0 && gameTypes.length < ALL_GAME_TYPES.length) {
      params.game_types = gameTypes;
    }
    if (gamePhases.length > 0 && gamePhases.length < ALL_GAME_PHASES.length) {
      params.game_phases = gamePhases;
    }
    return params;
  }, [dateState, gameTypes, gamePhases]);

  return {
    datePreset: dateState.preset,
    dateFrom: dateState.from,
    dateTo: dateState.to,
    gameTypes,
    gamePhases,
    setDatePreset,
    setCustomDateRange,
    clearDateFilter,
    setGameTypes,
    setGamePhases,
    getParams,
  };
}
