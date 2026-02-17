import { bus } from '../event-bus.js';

const STORAGE_KEY = 'dashboard-date-filter';

let currentDateFrom = null;
let currentDateTo = null;

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getPresetDates(preset) {
  const now = new Date();
  const to = now.toISOString().split('T')[0];
  let from = null;

  switch (preset) {
    case '7d':
      from = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '30d':
      from = new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '90d':
      from = new Date(now - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '1y':
      from = new Date(now - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case 'all':
      return { from: null, to: null };
  }
  return { from, to };
}

function updatePresetButtons(activePreset) {
  document.querySelectorAll('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === activePreset);
  });
}

function updateCustomToggle(active) {
  const customToggle = document.getElementById('customDateToggle');
  if (customToggle) customToggle.classList.toggle('active', active);
}

function collapseCustomRow() {
  const customRow = document.getElementById('customDateRow');
  if (customRow) customRow.classList.add('collapsed');
}

export function setPreset(preset) {
  const dates = getPresetDates(preset);
  document.getElementById('dateFrom').value = dates.from || '';
  document.getElementById('dateTo').value = dates.to || '';
  currentDateFrom = dates.from;
  currentDateTo = dates.to;

  updatePresetButtons(preset);
  updateCustomToggle(false);
  saveState({ type: 'preset', preset });
  bus.emit('dashboard:reload');
}

export function applyDateFilter() {
  currentDateFrom = document.getElementById('dateFrom').value || null;
  currentDateTo = document.getElementById('dateTo').value || null;

  updatePresetButtons(null);
  collapseCustomRow();
  updateCustomToggle(!!(currentDateFrom || currentDateTo));
  saveState({ type: 'custom', from: currentDateFrom, to: currentDateTo });
  bus.emit('dashboard:reload');
}

export function clearDateFilter() {
  document.getElementById('dateFrom').value = '';
  document.getElementById('dateTo').value = '';
  currentDateFrom = null;
  currentDateTo = null;

  updatePresetButtons('all');
  updateCustomToggle(false);
  collapseCustomRow();
  saveState({ type: 'preset', preset: 'all' });
  bus.emit('dashboard:reload');
}

export function dateParams() {
  const params = {};
  if (currentDateFrom) params.start_date = currentDateFrom;
  if (currentDateTo) params.end_date = currentDateTo;
  return params;
}

export function dateAndGameTypeParams(gameTypeFilters) {
  const params = dateParams();
  if (gameTypeFilters.length > 0 && gameTypeFilters.length < 4) {
    params.game_types = gameTypeFilters;
  }
  return params;
}

export function allFilterParams(gameTypeFilters, gamePhaseFilters) {
  const params = dateParams();
  if (gameTypeFilters.length > 0 && gameTypeFilters.length < 4) {
    params.game_types = gameTypeFilters;
  }
  if (gamePhaseFilters.length > 0 && gamePhaseFilters.length < 3) {
    params.game_phases = gamePhaseFilters;
  }
  return params;
}

function restoreState() {
  const state = loadState();
  if (!state) return;

  if (state.type === 'preset' && state.preset) {
    const dates = getPresetDates(state.preset);
    document.getElementById('dateFrom').value = dates.from || '';
    document.getElementById('dateTo').value = dates.to || '';
    currentDateFrom = dates.from;
    currentDateTo = dates.to;
    updatePresetButtons(state.preset);
    updateCustomToggle(false);
  } else if (state.type === 'custom') {
    document.getElementById('dateFrom').value = state.from || '';
    document.getElementById('dateTo').value = state.to || '';
    currentDateFrom = state.from || null;
    currentDateTo = state.to || null;
    updatePresetButtons(null);
    updateCustomToggle(!!(currentDateFrom || currentDateTo));
  }
}

export function initDateFilters() {
  document.getElementById('applyDateBtn').addEventListener('click', applyDateFilter);
  document.getElementById('clearDateBtn').addEventListener('click', clearDateFilter);
  document.querySelectorAll('.filter-presets button[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => setPreset(btn.dataset.preset));
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
