import { bus } from '../event-bus.js';
import { FilterPersistence } from '../filter-persistence.js';

const COLOR_FILTER_STORAGE_KEY = 'blunder-tutor-color-filter';
const FILTERS_COLLAPSED_KEY = 'blunder-tutor-filters-collapsed';
const PLAY_FULL_LINE_KEY = 'blunder-tutor-play-full-line';
const BOARD_SETTINGS_COLLAPSED_KEY = 'boardSettingsCollapsed';
const SHOW_COORDINATES_KEY = 'blunder-tutor-show-coordinates';

let currentPhaseFilters = [];
let currentTacticalFilter = 'all';
let currentGameTypeFilters = [];
let currentColorFilter = 'both';
let currentDifficultyFilters = [];
let filtersCollapsed = true;
let boardSettingsCollapsed = true;

const phaseFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-phase-filters',
  checkboxSelector: '.phase-filter-checkbox',
  defaultValues: [],
});

const gameTypeFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-game-type-filters',
  checkboxSelector: '.game-type-checkbox',
  defaultValues: ['bullet', 'blitz', 'rapid'],
});

const difficultyFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-difficulty-filters',
  checkboxSelector: '.difficulty-filter-checkbox',
  defaultValues: ['easy', 'medium', 'hard'],
});

export function getFilterParams() {
  const params = {};
  if (currentPhaseFilters.length > 0) params.game_phases = currentPhaseFilters;
  if (currentTacticalFilter && currentTacticalFilter !== 'all') params.tactical_patterns = currentTacticalFilter;
  if (currentGameTypeFilters.length > 0) params.game_types = currentGameTypeFilters;
  if (currentColorFilter && currentColorFilter !== 'both') params.colors = currentColorFilter;
  if (currentDifficultyFilters.length > 0) params.difficulties = currentDifficultyFilters;
  return params;
}

export function hasActiveFilters() {
  const hasTactical = currentTacticalFilter && currentTacticalFilter !== 'all';
  const hasPhase = currentPhaseFilters.length > 0 && currentPhaseFilters.length < 3;
  const hasGameType = currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4;
  const hasColor = currentColorFilter && currentColorFilter !== 'both';
  const hasDifficulty = currentDifficultyFilters.length > 0 && currentDifficultyFilters.length < 3;
  return hasTactical || hasPhase || hasGameType || hasColor || hasDifficulty;
}

export function updateFilterCountBadge() {
  const badge = document.getElementById('filtersCountBadge');
  if (!badge) return;
  let count = 0;
  if (currentTacticalFilter && currentTacticalFilter !== 'all') count++;
  if (currentPhaseFilters.length > 0 && currentPhaseFilters.length < 3) count++;
  if (currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4) count++;
  if (currentColorFilter && currentColorFilter !== 'both') count++;
  if (currentDifficultyFilters.length > 0 && currentDifficultyFilters.length < 3) count++;
  badge.textContent = count > 0 ? count + ' active' : '0 active';
  badge.classList.toggle('hidden', count === 0);
}

export function clearAllFilters() {
  currentTacticalFilter = 'all';
  localStorage.removeItem('blunder-tutor-tactical-filter');
  document.querySelectorAll('.tactical-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.pattern === 'all');
  });

  currentPhaseFilters = phaseFilter.reset(['opening', 'middlegame', 'endgame']);
  currentGameTypeFilters = gameTypeFilter.reset(['bullet', 'blitz', 'rapid']);

  currentColorFilter = 'both';
  localStorage.removeItem(COLOR_FILTER_STORAGE_KEY);
  document.querySelectorAll('input[name="colorFilter"]').forEach(radio => {
    radio.checked = radio.value === 'both';
  });

  currentDifficultyFilters = difficultyFilter.reset(['easy', 'medium', 'hard']);

  bus.emit('filters:changed');
}

export function isPlayFullLineEnabled() {
  const el = document.getElementById('playFullLine');
  return el && el.checked;
}

function toggleFiltersPanel() {
  filtersCollapsed = !filtersCollapsed;
  const content = document.getElementById('filtersContent');
  const chevron = document.getElementById('filtersChevron');
  if (content) content.classList.toggle('collapsed', filtersCollapsed);
  if (chevron) chevron.classList.toggle('collapsed', filtersCollapsed);
  localStorage.setItem(FILTERS_COLLAPSED_KEY, JSON.stringify(filtersCollapsed));
}

function loadFiltersPanelState() {
  const stored = localStorage.getItem(FILTERS_COLLAPSED_KEY);
  if (stored) {
    try { filtersCollapsed = JSON.parse(stored); } catch { filtersCollapsed = true; }
  }
  const content = document.getElementById('filtersContent');
  const chevron = document.getElementById('filtersChevron');
  if (content) content.classList.toggle('collapsed', filtersCollapsed);
  if (chevron) chevron.classList.toggle('collapsed', filtersCollapsed);
}

function toggleBoardSettingsPanel() {
  boardSettingsCollapsed = !boardSettingsCollapsed;
  const content = document.getElementById('boardSettingsContent');
  const chevron = document.getElementById('boardSettingsChevron');
  if (content) content.classList.toggle('collapsed', boardSettingsCollapsed);
  if (chevron) chevron.classList.toggle('collapsed', boardSettingsCollapsed);
  localStorage.setItem(BOARD_SETTINGS_COLLAPSED_KEY, JSON.stringify(boardSettingsCollapsed));
}

function loadBoardSettingsPanelState() {
  const stored = localStorage.getItem(BOARD_SETTINGS_COLLAPSED_KEY);
  if (stored) {
    try {
      boardSettingsCollapsed = JSON.parse(stored);
      const content = document.getElementById('boardSettingsContent');
      const chevron = document.getElementById('boardSettingsChevron');
      if (!boardSettingsCollapsed) {
        if (content) content.classList.remove('collapsed');
        if (chevron) chevron.classList.remove('collapsed');
      }
    } catch { boardSettingsCollapsed = true; }
  }
}

function loadTacticalFilterFromStorage() {
  const stored = localStorage.getItem('blunder-tutor-tactical-filter');
  if (stored) {
    currentTacticalFilter = stored;
    document.querySelectorAll('.tactical-filter-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.pattern === stored);
    });
  }
}

function loadColorFilterFromStorage() {
  const stored = localStorage.getItem(COLOR_FILTER_STORAGE_KEY);
  if (stored && (stored === 'white' || stored === 'black')) {
    currentColorFilter = stored;
  } else {
    currentColorFilter = 'both';
  }
  document.querySelectorAll('input[name="colorFilter"]').forEach(radio => {
    radio.checked = radio.value === currentColorFilter;
  });
}

function loadPlayFullLineSetting() {
  const el = document.getElementById('playFullLine');
  if (!el) return;
  el.checked = localStorage.getItem(PLAY_FULL_LINE_KEY) === 'true';
}

function loadShowCoordinatesSetting() {
  const el = document.getElementById('showCoordinates');
  if (!el) return;
  el.checked = localStorage.getItem(SHOW_COORDINATES_KEY) === 'true';
}

export function getShowCoordinates() {
  return localStorage.getItem(SHOW_COORDINATES_KEY) === 'true';
}

export function initFilters() {
  currentPhaseFilters = phaseFilter.load();
  loadTacticalFilterFromStorage();
  currentGameTypeFilters = gameTypeFilter.load();
  currentDifficultyFilters = difficultyFilter.load();
  loadColorFilterFromStorage();
  loadFiltersPanelState();
  loadBoardSettingsPanelState();
  loadPlayFullLineSetting();
  loadShowCoordinatesSetting();
  updateFilterCountBadge();

  document.querySelectorAll('.phase-filter-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      currentPhaseFilters = phaseFilter.save();
      bus.emit('filters:changed');
    });
  });

  document.querySelectorAll('.tactical-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tactical-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTacticalFilter = btn.dataset.pattern;
      localStorage.setItem('blunder-tutor-tactical-filter', currentTacticalFilter);
      bus.emit('filters:changed');
    });
  });

  document.querySelectorAll('.game-type-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      currentGameTypeFilters = gameTypeFilter.save();
      bus.emit('filters:changed');
    });
  });

  document.querySelectorAll('.difficulty-filter-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      currentDifficultyFilters = difficultyFilter.save();
      bus.emit('filters:changed');
    });
  });

  document.querySelectorAll('input[name="colorFilter"]').forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('input[name="colorFilter"]').forEach(r => {
        if (r.checked) currentColorFilter = r.value;
      });
      if (currentColorFilter === 'both') {
        localStorage.removeItem(COLOR_FILTER_STORAGE_KEY);
      } else {
        localStorage.setItem(COLOR_FILTER_STORAGE_KEY, currentColorFilter);
      }
      bus.emit('filters:changed');
    });
  });

  const filtersHeader = document.getElementById('filtersHeader');
  const filtersToggleBtn = document.getElementById('filtersToggleBtn');
  if (filtersHeader) filtersHeader.addEventListener('click', toggleFiltersPanel);
  if (filtersToggleBtn) {
    filtersToggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFiltersPanel();
    });
  }

  const boardSettingsHeader = document.getElementById('boardSettingsHeader');
  const boardSettingsToggleBtn = document.getElementById('boardSettingsToggleBtn');
  if (boardSettingsHeader) boardSettingsHeader.addEventListener('click', toggleBoardSettingsPanel);
  if (boardSettingsToggleBtn) {
    boardSettingsToggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleBoardSettingsPanel();
    });
  }

  const playFullLineCheckbox = document.getElementById('playFullLine');
  if (playFullLineCheckbox) {
    playFullLineCheckbox.addEventListener('change', () => {
      localStorage.setItem(PLAY_FULL_LINE_KEY, playFullLineCheckbox.checked ? 'true' : 'false');
    });
  }

  const showCoordinatesCheckbox = document.getElementById('showCoordinates');
  if (showCoordinatesCheckbox) {
    showCoordinatesCheckbox.addEventListener('change', () => {
      localStorage.setItem(SHOW_COORDINATES_KEY, showCoordinatesCheckbox.checked ? 'true' : 'false');
      bus.emit('coordinates:changed');
    });
  }
}
