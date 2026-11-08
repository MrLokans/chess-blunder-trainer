import { useState, useCallback, useRef } from 'preact/hooks';
import { GAME_TYPES, GAME_PHASES, DIFFICULTIES } from '../../shared/constants';
import { STORAGE_KEYS } from '../../shared/storage-keys';
import { loadFromStorage } from '../../hooks/useFilterPersistence';
import { loadBoardDisplay, saveBoardDisplay } from '../../shared/board-display';

export type QueryParams = Record<string, string | number | boolean | null | undefined | string[]>;

interface FilterState {
  phases: string[];
  gameTypes: string[];
  difficulties: string[];
  tacticalPattern: string | null;
  color: string;
  showCoordinates: boolean;
  showArrows: boolean;
  showThreats: boolean;
  showTactics: boolean;
}

const SK = {
  phases: STORAGE_KEYS.trainerPhases,
  gameTypes: STORAGE_KEYS.trainerGameTypes,
  difficulties: STORAGE_KEYS.trainerDifficulties,
  tactical: STORAGE_KEYS.trainerTactical,
  color: STORAGE_KEYS.trainerColor,
} as const;

function loadString(key: string, defaultVal: string): string {
  return localStorage.getItem(key) ?? defaultVal;
}

const DEFAULT_PHASES = [...GAME_PHASES];
const DEFAULT_GAME_TYPES = [...GAME_TYPES];
const DEFAULT_DIFFICULTIES = [...DIFFICULTIES];

export interface FiltersAPI {
  state: FilterState;
  getFilterParams: () => QueryParams;
  clearAllFilters: () => void;
  setPhases: (phases: string[]) => void;
  setGameTypes: (types: string[]) => void;
  setDifficulties: (diffs: string[]) => void;
  setTacticalPattern: (pattern: string | null) => void;
  focusTacticalPattern: (pattern: string) => void;
  setColor: (color: string) => void;
  setShowArrows: (enabled: boolean) => void;
  setShowThreats: (enabled: boolean) => void;
}

export function useFilters(onFilterChange: () => void): FiltersAPI {
  const [state, setState] = useState<FilterState>(() => ({
    phases: loadFromStorage(SK.phases, DEFAULT_PHASES),
    gameTypes: loadFromStorage(SK.gameTypes, DEFAULT_GAME_TYPES),
    difficulties: loadFromStorage(SK.difficulties, DEFAULT_DIFFICULTIES),
    tacticalPattern: loadString(SK.tactical, '') || null,
    color: loadString(SK.color, 'both'),
    showCoordinates: loadBoardDisplay('showCoordinates'),
    showArrows: loadBoardDisplay('showArrows'),
    showThreats: loadBoardDisplay('showThreats'),
    showTactics: loadBoardDisplay('showTactics'),
  }));

  const persist = useCallback((key: string, value: unknown) => {
    if (Array.isArray(value) || typeof value === 'object') {
      localStorage.setItem(key, JSON.stringify(value));
    } else {
      localStorage.setItem(key, typeof value === 'boolean' || typeof value === 'number' ? String(value) : (value as string));
    }
  }, []);

  // After a deep link, the first drawer edit saves the whole filter set the user sees, not one field over the hidden saved ones.
  const focusedPatternRef = useRef<string | null>(null);
  const save = useCallback((key: string, value: unknown) => {
    const focused = focusedPatternRef.current;
    if (focused !== null) {
      focusedPatternRef.current = null;
      persist(SK.phases, DEFAULT_PHASES);
      persist(SK.gameTypes, DEFAULT_GAME_TYPES);
      persist(SK.difficulties, DEFAULT_DIFFICULTIES);
      persist(SK.tactical, focused);
      persist(SK.color, 'both');
    }
    persist(key, value);
  }, [persist]);

  const setPhases = useCallback((phases: string[]) => {
    setState(s => ({ ...s, phases }));
    save(SK.phases, phases);
    onFilterChange();
  }, [save, onFilterChange]);

  const setGameTypes = useCallback((types: string[]) => {
    setState(s => ({ ...s, gameTypes: types }));
    save(SK.gameTypes, types);
    onFilterChange();
  }, [save, onFilterChange]);

  const setDifficulties = useCallback((diffs: string[]) => {
    setState(s => ({ ...s, difficulties: diffs }));
    save(SK.difficulties, diffs);
    onFilterChange();
  }, [save, onFilterChange]);

  const setTacticalPattern = useCallback((pattern: string | null) => {
    setState(s => ({ ...s, tacticalPattern: pattern }));
    save(SK.tactical, pattern ?? '');
    onFilterChange();
  }, [save, onFilterChange]);

  // A deep link shows every blunder of the pattern, so saved filters are set aside for this visit and kept in storage.
  const focusTacticalPattern = useCallback((pattern: string) => {
    setState(s => ({
      ...s,
      phases: DEFAULT_PHASES,
      gameTypes: DEFAULT_GAME_TYPES,
      difficulties: DEFAULT_DIFFICULTIES,
      tacticalPattern: pattern,
      color: 'both',
    }));
    focusedPatternRef.current = pattern;
    onFilterChange();
  }, [onFilterChange]);

  const setColor = useCallback((color: string) => {
    setState(s => ({ ...s, color }));
    save(SK.color, color);
    onFilterChange();
  }, [save, onFilterChange]);

  const setShowArrows = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showArrows: enabled }));
    saveBoardDisplay('showArrows', enabled);
  }, []);

  const setShowThreats = useCallback((enabled: boolean) => {
    setState(s => ({ ...s, showThreats: enabled }));
    saveBoardDisplay('showThreats', enabled);
  }, []);

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

  const clearAllFilters = useCallback(() => {
    focusedPatternRef.current = null;
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
    state, getFilterParams, clearAllFilters,
    setPhases, setGameTypes, setDifficulties, setTacticalPattern, focusTacticalPattern, setColor,
    setShowArrows, setShowThreats,
  };
}
