import { client } from './api.js';

const METRICS = [
  { key: 'avg_blunders_per_game', i18n: 'growth.blunders_per_game', trendKey: 'blunder_frequency', precision: 2, lowerIsBetter: true },
  { key: 'avg_cpl',              i18n: 'growth.avg_cpl',            trendKey: 'move_quality',       precision: 1, lowerIsBetter: true, helpBtnId: 'cplHelpBtn' },
  { key: 'avg_blunder_severity', i18n: 'growth.blunder_severity',   trendKey: 'severity',           precision: 1, lowerIsBetter: true },
  { key: 'clean_game_rate',      i18n: 'growth.clean_game_rate',    trendKey: 'clean_rate',         precision: 1, lowerIsBetter: false, suffix: '%' },
  { key: 'catastrophic_rate',    i18n: 'growth.catastrophic_rate',  trendKey: 'catastrophic_rate',  precision: 1, lowerIsBetter: true,  suffix: '%' },
];

function buildSparklineSvg(values) {
  if (values.length < 2) return '';
  const width = 120;
  const height = 36;
  const pad = 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - 2 * pad);
    const y = pad + (1 - (v - min) / range) * (height - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return `<svg class="growth-sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
    <polyline points="${points}" fill="none" stroke="var(--primary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
}

function renderTrendArrow(direction, lowerIsBetter) {
  if (!direction || direction === 'stable') {
    return direction === 'stable'
      ? `<span class="growth-trend growth-trend--stable" title="${t('growth.stable')}">→</span>`
      : '';
  }

  // Arrow shows value direction, color shows good/bad
  const valueWentDown = (direction === 'improving') === lowerIsBetter;
  const symbol = valueWentDown ? '↓' : '↑';
  const isGood = direction === 'improving';
  const cssClass = isGood ? 'growth-trend--improving' : 'growth-trend--declining';
  const label = t('growth.' + direction);

  return `<span class="growth-trend ${cssClass}" title="${label}">${symbol}</span>`;
}

export function renderGrowthMetrics(data) {
  const container = document.getElementById('growthMetricsContent');
  if (!container) return;

  if (data.total_games === 0) {
    container.innerHTML = `<div class="no-data-message">${t('growth.no_data')}</div>`;
    return;
  }

  if (data.windows.length === 0) {
    container.innerHTML = `<div class="no-data-message">${t('growth.insufficient_data', { count: data.window_size })}</div>`;
    return;
  }

  const rows = METRICS.map(metric => {
    const values = data.windows.map(w => w[metric.key]);
    const current = values[values.length - 1];
    const suffix = metric.suffix || '';
    const trendDir = metric.trendKey && data.trend ? data.trend[metric.trendKey] : null;
    const helpBtn = metric.helpBtnId
      ? ` <button class="info-help-btn" id="${metric.helpBtnId}" aria-label="${t('growth.cpl_help_label')}">?</button>`
      : '';

    return `
      <div class="growth-metric-row">
        <span class="growth-metric-label">${t(metric.i18n)}${helpBtn}</span>
        ${buildSparklineSvg(values)}
        <span class="growth-value">${current.toFixed(metric.precision)}${suffix}</span>
        ${renderTrendArrow(trendDir, metric.lowerIsBetter)}
      </div>
    `;
  }).join('');

  const insufficientTrend = data.windows.length < 2
    ? `<div class="growth-insufficient">${t('growth.insufficient_data', { count: data.window_size * 2 })}</div>`
    : '';

  container.innerHTML = rows + insufficientTrend;

  initCplHelpModal();
}

function initCplHelpModal() {
  const btn = document.getElementById('cplHelpBtn');
  const overlay = document.getElementById('cplHelpOverlay');
  const close = document.getElementById('cplHelpClose');
  if (!btn || !overlay) return;

  btn.addEventListener('click', () => overlay.classList.add('visible'));
  close?.addEventListener('click', () => overlay.classList.remove('visible'));
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.remove('visible');
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('visible')) {
      overlay.classList.remove('visible');
    }
  });
}

export async function loadGrowthMetrics(filterParams) {
  try {
    const data = await client.stats.growth(filterParams);
    renderGrowthMetrics(data);
  } catch (err) {
    console.error('Failed to load growth metrics:', err);
    const container = document.getElementById('growthMetricsContent');
    if (container) container.innerHTML = '';
  }
}
