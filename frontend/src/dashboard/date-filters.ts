import { bus } from '../shared/event-bus';

const STORAGE_KEY = 'dashboard-date-filter';

type DatePreset = '7d' | '30d' | '90d' | '1y' | 'all';

interface PresetState {
  type: 'preset';
  preset: DatePreset;
}

interface CustomState {
  type: 'custom';
  from: string | null;
  to: string | null;
}

type FilterState = PresetState | CustomState;

interface DateRange {
  from: string | null;
  to: string | null;
}

export interface DateFilterParams {
  start_date?: string;
  end_date?: string;
  game_types?: string[];
  game_phases?: string[];
  [key: string]: string | number | boolean | null | undefined | string[];
}

let currentDateFrom: string | null = null;
let currentDateTo: string | null = null;

function saveState(state: FilterState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function loadState(): FilterState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) as FilterState : null;
  } catch {
    return null;
  }
}

export function getPresetDates(preset: string): DateRange {
  const now = new Date();
  const to = now.toISOString().split('T')[0]!;
  let from: string | null = null;

  switch (preset) {
    case '7d':
      from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]!;
      break;
    case '30d':
      from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]!;
      break;
    case '90d':
      from = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]!;
      break;
    case '1y':
      from = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]!;
      break;
    case 'all':
      return { from: null, to: null };
  }
  return { from, to };
}

function updatePresetButtons(activePreset: string | null): void {
  document.querySelectorAll<HTMLButtonElement>('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset['preset'] === activePreset);
  });
}

function updateCustomToggle(active: boolean): void {
  const customToggle = document.getElementById('customDateToggle');
  if (customToggle) customToggle.classList.toggle('active', active);
}

function collapseCustomRow(): void {
  const customRow = document.getElementById('customDateRow');
  if (customRow) customRow.classList.add('collapsed');
}

export function setPreset(preset: string): void {
  const dates = getPresetDates(preset);
  (document.getElementById('dateFrom') as HTMLInputElement).value = dates.from || '';
  (document.getElementById('dateTo') as HTMLInputElement).value = dates.to || '';
  currentDateFrom = dates.from;
  currentDateTo = dates.to;

  updatePresetButtons(preset);
  updateCustomToggle(false);
  saveState({ type: 'preset', preset: preset as DatePreset });
  bus.emit('dashboard:reload');
}

export function applyDateFilter(): void {
  currentDateFrom = (document.getElementById('dateFrom') as HTMLInputElement).value || null;
  currentDateTo = (document.getElementById('dateTo') as HTMLInputElement).value || null;

  updatePresetButtons(null);
  collapseCustomRow();
  updateCustomToggle(!!(currentDateFrom || currentDateTo));
  saveState({ type: 'custom', from: currentDateFrom, to: currentDateTo });
  bus.emit('dashboard:reload');
}

export function clearDateFilter(): void {
  (document.getElementById('dateFrom') as HTMLInputElement).value = '';
  (document.getElementById('dateTo') as HTMLInputElement).value = '';
  currentDateFrom = null;
  currentDateTo = null;

  updatePresetButtons('all');
  updateCustomToggle(false);
  collapseCustomRow();
  saveState({ type: 'preset', preset: 'all' });
  bus.emit('dashboard:reload');
}

export function dateParams(): DateFilterParams {
  const params: DateFilterParams = {};
  if (currentDateFrom) params.start_date = currentDateFrom;
  if (currentDateTo) params.end_date = currentDateTo;
  return params;
}

export function dateAndGameTypeParams(gameTypeFilters: string[]): DateFilterParams {
  const params = dateParams();
  if (gameTypeFilters.length > 0 && gameTypeFilters.length < 4) {
    params.game_types = gameTypeFilters;
  }
  return params;
}

export function allFilterParams(gameTypeFilters: string[], gamePhaseFilters: string[]): DateFilterParams {
  const params = dateParams();
  if (gameTypeFilters.length > 0 && gameTypeFilters.length < 4) {
    params.game_types = gameTypeFilters;
  }
  if (gamePhaseFilters.length > 0 && gamePhaseFilters.length < 3) {
    params.game_phases = gamePhaseFilters;
  }
  return params;
}

function restoreState(): void {
  const state = loadState();
  if (!state) return;

  if (state.type === 'preset' && state.preset) {
    const dates = getPresetDates(state.preset);
    (document.getElementById('dateFrom') as HTMLInputElement).value = dates.from || '';
    (document.getElementById('dateTo') as HTMLInputElement).value = dates.to || '';
    currentDateFrom = dates.from;
    currentDateTo = dates.to;
    updatePresetButtons(state.preset);
    updateCustomToggle(false);
  } else if (state.type === 'custom') {
    (document.getElementById('dateFrom') as HTMLInputElement).value = state.from || '';
    (document.getElementById('dateTo') as HTMLInputElement).value = state.to || '';
    currentDateFrom = state.from || null;
    currentDateTo = state.to || null;
    updatePresetButtons(null);
    updateCustomToggle(!!(currentDateFrom || currentDateTo));
  }
}

export function initDateFilters(): void {
  document.getElementById('applyDateBtn')!.addEventListener('click', applyDateFilter);
  document.getElementById('clearDateBtn')!.addEventListener('click', clearDateFilter);
  document.querySelectorAll<HTMLButtonElement>('.filter-presets button[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => setPreset(btn.dataset['preset']!));
  });

  const customToggle = document.getElementById('customDateToggle');
  const customRow = document.getElementById('customDateRow');
  if (customToggle && customRow) {
    customToggle.addEventListener('click', () => {
      const isCollapsed = customRow.classList.toggle('collapsed');
      customToggle.classList.toggle('active', !isCollapsed);
    });
  }

  restoreState();
}
