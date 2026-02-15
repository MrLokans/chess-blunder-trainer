import { bus } from '../event-bus.js';

let currentDateFrom = null;
let currentDateTo = null;

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

export function setPreset(preset) {
  const dates = getPresetDates(preset);
  document.getElementById('dateFrom').value = dates.from || '';
  document.getElementById('dateTo').value = dates.to || '';
  currentDateFrom = dates.from;
  currentDateTo = dates.to;

  document.querySelectorAll('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset);
  });

  bus.emit('dashboard:reload');
}

export function applyDateFilter() {
  currentDateFrom = document.getElementById('dateFrom').value || null;
  currentDateTo = document.getElementById('dateTo').value || null;
  document.querySelectorAll('.filter-presets button').forEach(btn => btn.classList.remove('active'));
  bus.emit('dashboard:reload');
}

export function clearDateFilter() {
  document.getElementById('dateFrom').value = '';
  document.getElementById('dateTo').value = '';
  currentDateFrom = null;
  currentDateTo = null;

  document.querySelectorAll('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === 'all');
  });

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

export function initDateFilters() {
  document.getElementById('applyDateBtn').addEventListener('click', applyDateFilter);
  document.getElementById('clearDateBtn').addEventListener('click', clearDateFilter);
  document.querySelectorAll('.filter-presets button[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => setPreset(btn.dataset.preset));
  });
}
