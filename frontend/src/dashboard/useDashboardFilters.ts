import { useState, useCallback } from 'preact/hooks';
import type { DateFilterParams, DatePreset } from './types';
import { GAME_TYPES, GAME_PHASES } from '../shared/constants';
import { STORAGE_KEYS } from '../shared/storage-keys';
import { loadFromStorage } from '../hooks/useFilterPersistence';

const DATE_STORAGE_KEY = STORAGE_KEYS.dashboardDate;
const GAME_TYPE_STORAGE_KEY = STORAGE_KEYS.dashboardGameTypes;
const GAME_PHASE_STORAGE_KEY = STORAGE_KEYS.dashboardGamePhases;

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
  const [gameTypes, setGameTypesState] = useState(() => loadFromStorage(GAME_TYPE_STORAGE_KEY, GAME_TYPES));
  const [gamePhases, setGamePhasesState] = useState(() => loadFromStorage(GAME_PHASE_STORAGE_KEY, GAME_PHASES));

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
    if (gameTypes.length > 0 && gameTypes.length < GAME_TYPES.length) {
      params.game_types = gameTypes;
    }
    if (gamePhases.length > 0 && gamePhases.length < GAME_PHASES.length) {
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
