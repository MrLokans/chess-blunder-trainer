import { useState, useCallback } from 'preact/hooks';

type QueryParams = Record<string, string | number | boolean | null | undefined | string[]>;

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

const STORAGE_KEYS = {
  phases: 'blunder-tutor-phase-filters',
  gameTypes: 'blunder-tutor-game-type-filters',
  difficulties: 'blunder-tutor-difficulty-filters',
  tactical: 'blunder-tutor-tactical-filter',
  color: 'blunder-tutor-color-filter',
  filtersCollapsed: 'blunder-tutor-filters-collapsed',
  playFullLine: 'blunder-tutor-play-full-line',
  boardSettingsCollapsed: 'boardSettingsCollapsed',
  showCoordinates: 'blunder-tutor-show-coordinates',
} as const;

function loadArray(key: string, defaults: string[]): string[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : defaults;
  } catch { return defaults; }
}

function loadBool(key: string, defaultVal: boolean): boolean {
  const raw = localStorage.getItem(key);
  if (raw === null) return defaultVal;
  return raw === 'true';
}

function loadString(key: string, defaultVal: string): string {
  return localStorage.getItem(key) ?? defaultVal;
}

const DEFAULT_PHASES = ['opening', 'middlegame', 'endgame'];
const DEFAULT_GAME_TYPES = ['bullet', 'blitz', 'rapid', 'classical'];
const DEFAULT_DIFFICULTIES = ['easy', 'medium', 'hard'];

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
    phases: loadArray(STORAGE_KEYS.phases, DEFAULT_PHASES),
    gameTypes: loadArray(STORAGE_KEYS.gameTypes, DEFAULT_GAME_TYPES),
    difficulties: loadArray(STORAGE_KEYS.difficulties, DEFAULT_DIFFICULTIES),
    tacticalPattern: loadString(STORAGE_KEYS.tactical, '') || null,
    color: loadString(STORAGE_KEYS.color, 'both'),
    playFullLine: loadBool(STORAGE_KEYS.playFullLine, false),
    showCoordinates: loadBool(STORAGE_KEYS.showCoordinates, true),
    showArrows: true,
    showThreats: false,
    showTactics: true,
    filtersCollapsed: loadBool(STORAGE_KEYS.filtersCollapsed, false),
    boardSettingsCollapsed: loadBool(STORAGE_KEYS.boardSettingsCollapsed, false),
  }));

  const persist = useCallback((key: string, value: unknown) => {
    if (Array.isArray(value) || typeof value === 'object') {
      localStorage.setItem(key, JSON.stringify(value));
    } else {
      localStorage.setItem(key, String(value));
    }
  }, []);

  const setPhases = useCallback((phases: string[]) => {
    setState(s => ({ ...s, phases }));
    persist(STORAGE_KEYS.phases, phases);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setGameTypes = useCallback((types: string[]) => {
    setState(s => ({ ...s, gameTypes: types }));
    persist(STORAGE_KEYS.gameTypes, types);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setDifficulties = useCallback((diffs: string[]) => {
    setState(s => ({ ...s, difficulties: diffs }));
    persist(STORAGE_KEYS.difficulties, diffs);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setTacticalPattern = useCallback((pattern: string | null) => {
    setState(s => ({ ...s, tacticalPattern: pattern }));
    persist(STORAGE_KEYS.tactical, pattern ?? '');
    onFilterChange();
  }, [persist, onFilterChange]);

  const setColor = useCallback((color: string) => {
    setState(s => ({ ...s, color }));
    persist(STORAGE_KEYS.color, color);
    onFilterChange();
  }, [persist, onFilterChange]);

  const setPlayFullLine = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, playFullLine: enabled }));
    persist(STORAGE_KEYS.playFullLine, enabled);
  }, [persist]);

  const setShowCoordinates = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showCoordinates: enabled }));
    persist(STORAGE_KEYS.showCoordinates, enabled);
  }, [persist]);

  const setShowArrows = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showArrows: enabled }));
  }, []);

  const setShowThreats = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showThreats: enabled }));
  }, []);

  const setShowTactics = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showTactics: enabled }));
  }, []);

  const toggleFiltersCollapsed = useCallback(() => {
    setState(s => {
      const next = !s.filtersCollapsed;
      persist(STORAGE_KEYS.filtersCollapsed, next);
      return { ...s, filtersCollapsed: next };
    });
  }, [persist]);

  const toggleBoardSettingsCollapsed = useCallback(() => {
    setState(s => {
      const next = !s.boardSettingsCollapsed;
      persist(STORAGE_KEYS.boardSettingsCollapsed, next);
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
    persist(STORAGE_KEYS.phases, DEFAULT_PHASES);
    persist(STORAGE_KEYS.gameTypes, DEFAULT_GAME_TYPES);
    persist(STORAGE_KEYS.difficulties, DEFAULT_DIFFICULTIES);
    persist(STORAGE_KEYS.tactical, '');
    persist(STORAGE_KEYS.color, 'both');
    onFilterChange();
  }, [persist, onFilterChange]);

  return {
    state, getFilterParams, hasActiveFilters, activeFilterCount, clearAllFilters,
    setPhases, setGameTypes, setDifficulties, setTacticalPattern, setColor,
    setPlayFullLine, setShowCoordinates, setShowArrows, setShowThreats, setShowTactics,
    toggleFiltersCollapsed, toggleBoardSettingsCollapsed,
  };
}
