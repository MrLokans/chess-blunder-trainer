import { useState, useCallback } from 'preact/hooks';
import { GAME_TYPES, GAME_PHASES, DIFFICULTIES } from '../../shared/constants';
import { STORAGE_KEYS } from '../../shared/storage-keys';
import { loadFromStorage } from '../../hooks/useFilterPersistence';

export type QueryParams = Record<string, string | number | boolean | null | undefined | string[]>;

interface FilterState {
  phases: string[];
  gameTypes: string[];
  difficulties: string[];
  tacticalPattern: string | null;
  color: string;
  playFullLine: boolean;
  showCoordinates: boolean;
  showArrows: boolean;
  showThreats: boolean;
  showTactics: boolean;
  filtersCollapsed: boolean;
  boardSettingsCollapsed: boolean;
}

const SK = {
  phases: STORAGE_KEYS.trainerPhases,
  gameTypes: STORAGE_KEYS.trainerGameTypes,
  difficulties: STORAGE_KEYS.trainerDifficulties,
  tactical: STORAGE_KEYS.trainerTactical,
  color: STORAGE_KEYS.trainerColor,
  filtersCollapsed: STORAGE_KEYS.trainerFiltersCollapsed,
  playFullLine: STORAGE_KEYS.trainerPlayFullLine,
  boardSettingsCollapsed: STORAGE_KEYS.trainerBoardSettingsCollapsed,
  showCoordinates: STORAGE_KEYS.trainerShowCoordinates,
  showArrows: STORAGE_KEYS.trainerShowArrows,
  showThreats: STORAGE_KEYS.trainerShowThreats,
  showTactics: STORAGE_KEYS.trainerShowTactics,
} as const;

function loadBool(key: string, defaultVal: boolean): boolean {
  const raw = localStorage.getItem(key);
  if (raw === null) return defaultVal;
  return raw === 'true';
}

function loadString(key: string, defaultVal: string): string {
  return localStorage.getItem(key) ?? defaultVal;
}

const DEFAULT_PHASES = [...GAME_PHASES];
const DEFAULT_GAME_TYPES = [...GAME_TYPES];
const DEFAULT_DIFFICULTIES = [...DIFFICULTIES];

export interface FiltersAPI {
  state: FilterState;
  getFilterParams: () => QueryParams;
  hasActiveFilters: () => boolean;
  activeFilterCount: () => number;
  clearAllFilters: () => void;
  setPhases: (phases: string[]) => void;
  setGameTypes: (types: string[]) => void;
  setDifficulties: (diffs: string[]) => void;
  setTacticalPattern: (pattern: string | null) => void;
  setColor: (color: string) => void;
  setPlayFullLine: (enabled: boolean) => void;
  setShowCoordinates: (enabled: boolean) => void;
  setShowArrows: (enabled: boolean) => void;
  setShowThreats: (enabled: boolean) => void;
  setShowTactics: (enabled: boolean) => void;
  toggleFiltersCollapsed: () => void;
  toggleBoardSettingsCollapsed: () => void;
}

export function useFilters(onFilterChange: () => void): FiltersAPI {
  const [state, setState] = useState<FilterState>(() => ({
    phases: loadFromStorage(SK.phases, DEFAULT_PHASES),
    gameTypes: loadFromStorage(SK.gameTypes, DEFAULT_GAME_TYPES),
    difficulties: loadFromStorage(SK.difficulties, DEFAULT_DIFFICULTIES),
    tacticalPattern: loadString(SK.tactical, '') || null,
    color: loadString(SK.color, 'both'),
    playFullLine: loadBool(SK.playFullLine, false),
    showCoordinates: loadBool(SK.showCoordinates, true),
    showArrows: loadBool(SK.showArrows, true),
    showThreats: loadBool(SK.showThreats, false),
    showTactics: loadBool(SK.showTactics, true),
    filtersCollapsed: loadBool(SK.filtersCollapsed, false),
    boardSettingsCollapsed: loadBool(SK.boardSettingsCollapsed, false),
  }));

  const persist = useCallback((key: string, value: unknown) => {
    if (Array.isArray(value) || typeof value === 'object') {
      localStorage.setItem(key, JSON.stringify(value));
    } else {
      localStorage.setItem(key, typeof value === 'boolean' || typeof value === 'number' ? String(value) : (value as string));
    }
  }, []);

  const setPhases = useCallback((phases: string[]) => {
    setState(s => ({ ...s, phases }));
    persist(SK.phases, phases);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setGameTypes = useCallback((types: string[]) => {
    setState(s => ({ ...s, gameTypes: types }));
    persist(SK.gameTypes, types);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setDifficulties = useCallback((diffs: string[]) => {
    setState(s => ({ ...s, difficulties: diffs }));
    persist(SK.difficulties, diffs);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setTacticalPattern = useCallback((pattern: string | null) => {
    setState(s => ({ ...s, tacticalPattern: pattern }));
    persist(SK.tactical, pattern ?? '');
    onFilterChange();
  }, [persist, onFilterChange]);

  const setColor = useCallback((color: string) => {
    setState(s => ({ ...s, color }));
    persist(SK.color, color);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setPlayFullLine = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, playFullLine: enabled }));
    persist(SK.playFullLine, enabled);
  }, [persist]);

  const setShowCoordinates = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showCoordinates: enabled }));
    persist(SK.showCoordinates, enabled);
  }, [persist]);

  const setShowArrows = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showArrows: enabled }));
    persist(SK.showArrows, enabled);
  }, [persist]);

  const setShowThreats = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showThreats: enabled }));
    persist(SK.showThreats, enabled);
  }, [persist]);

  const setShowTactics = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showTactics: enabled }));
    persist(SK.showTactics, enabled);
  }, [persist]);

  const toggleFiltersCollapsed = useCallback(() => {
    setState(s => {
      const next = !s.filtersCollapsed;
      persist(SK.filtersCollapsed, next);
      return { ...s, filtersCollapsed: next };
    });
  }, [persist]);

  const toggleBoardSettingsCollapsed = useCallback(() => {
    setState(s => {
      const next = !s.boardSettingsCollapsed;
      persist(SK.boardSettingsCollapsed, next);
      return { ...s, boardSettingsCollapsed: next };
    });
  }, [persist]);

  const getFilterParams = useCallback((): QueryParams => {
    const params: QueryParams = {};
    if (state.phases.length > 0 && state.phases.length < DEFAULT_PHASES.length) {
      params.game_phases = state.phases;
    }
    if (state.gameTypes.length > 0 && state.gameTypes.length < DEFAULT_GAME_TYPES.length) {
      params.game_types = state.gameTypes;
    }
    if (state.difficulties.length > 0 && state.difficulties.length < DEFAULT_DIFFICULTIES.length) {
      params.difficulties = state.difficulties;
    }
    if (state.tacticalPattern) {
      params.tactical_patterns = [state.tacticalPattern];
    }
    if (state.color !== 'both') {
      params.colors = [state.color];
    }
    return params;
  }, [state.phases, state.gameTypes, state.difficulties, state.tacticalPattern, state.color]);

  const activeFilterCount = useCallback((): number => {
    let count = 0;
    if (state.phases.length < DEFAULT_PHASES.length) count++;
    if (state.gameTypes.length < DEFAULT_GAME_TYPES.length) count++;
    if (state.difficulties.length < DEFAULT_DIFFICULTIES.length) count++;
    if (state.tacticalPattern) count++;
    if (state.color !== 'both') count++;
    return count;
  }, [state.phases, state.gameTypes, state.difficulties, state.tacticalPattern, state.color]);

  const hasActiveFilters = useCallback((): boolean => activeFilterCount() > 0, [activeFilterCount]);

  const clearAllFilters = useCallback(() => {
    setState(s => ({
      ...s,
      phases: DEFAULT_PHASES,
      gameTypes: DEFAULT_GAME_TYPES,
      difficulties: DEFAULT_DIFFICULTIES,
      tacticalPattern: null,
      color: 'both',
    }));
    persist(SK.phases, DEFAULT_PHASES);
    persist(SK.gameTypes, DEFAULT_GAME_TYPES);
    persist(SK.difficulties, DEFAULT_DIFFICULTIES);
    persist(SK.tactical, '');
    persist(SK.color, 'both');
    onFilterChange();
  }, [persist, onFilterChange]);

  return {
    state, getFilterParams, hasActiveFilters, activeFilterCount, clearAllFilters,
    setPhases, setGameTypes, setDifficulties, setTacticalPattern, setColor,
    setPlayFullLine, setShowCoordinates, setShowArrows, setShowThreats, setShowTactics,
    toggleFiltersCollapsed, toggleBoardSettingsCollapsed,
  };
}
