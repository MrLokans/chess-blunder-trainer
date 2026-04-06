import { bus } from '../shared/event-bus';
import { WebSocketClient } from '../shared/websocket-client';
import { FilterPersistence } from '../shared/filter-persistence';
import { client } from '../shared/api';
import { debounce } from '../shared/debounce';
import { hasFeature } from '../shared/features';
import { allFilterParams, initDateFilters } from './date-filters';
import type { DateFilterParams } from './date-filters';
import { createDateChart, createHourChart } from './charts';
import {
  renderPhaseBreakdown, renderColorBreakdown, renderGameTypeBreakdown,
  renderEcoBreakdown, renderTacticalBreakdown, renderDifficultyBreakdown,
  renderCollapsePoint, renderConversionResilience, renderTrapsSummary,
  renderGameBreakdown, initOpeningGroupToggles,
} from './renderers';
import type { BreakdownResult } from './renderers';

// These modules are not yet fully migrated; declare minimal signatures.
declare function loadHeatmap(containerId: string): Promise<void>;
declare function loadGrowthMetrics(params: DateFilterParams): Promise<void>;

const wsClient = new WebSocketClient();

let dateChart: ChartInstance | null = null;
let hourChart: ChartInstance | null = null;
let currentGameTypeFilters: string[] = ['bullet', 'blitz', 'rapid', 'classical'];
let currentGamePhaseFilters: string[] = ['opening', 'middlegame', 'endgame'];

const gameTypeFilter = new FilterPersistence({
  storageKey: 'dashboard-game-type-filters',
  checkboxSelector: '.game-type-filter',
  defaultValues: ['bullet', 'blitz', 'rapid', 'classical'],
});

const gamePhaseFilter = new FilterPersistence({
  storageKey: 'dashboard-game-phase-filters',
  checkboxSelector: '.game-phase-filter',
  defaultValues: ['opening', 'middlegame', 'endgame'],
});

function getParams(): DateFilterParams {
  return allFilterParams(currentGameTypeFilters, currentGamePhaseFilters);
}

function applyBreakdown(
  containerId: string,
  barContainerId: string,
  barId: string,
  legendId: string | null,
  result: BreakdownResult,
): void {
  const container = document.getElementById(containerId);
  const barContainer = document.getElementById(barContainerId);
  const bar = document.getElementById(barId);
  if (!container) return;

  container.innerHTML = result.cards;

  if (barContainer) {
    barContainer.classList.toggle('hidden', !result.showBar);
    if (bar && result.bar) bar.innerHTML = result.bar;
  }

  if (legendId) {
    const legend = document.getElementById(legendId);
    if (legend && result.legend) legend.innerHTML = result.legend;
  }
}

interface AnalysisStatus {
  status: string;
  progress_current?: number;
  progress_total?: number;
}

interface DateChartItem {
  date: string;
  game_count: number;
  avg_accuracy: number;
}

interface HourChartItem {
  hour: number;
  game_count: number;
  avg_accuracy: number;
}

interface OverviewData {
  total_games: number;
  analyzed_games: number;
  total_blunders: number;
}

const STATUS_COLOR_CLASSES = ['text-primary', 'text-success', 'text-error'];

function renderAnalysisStatus(status: AnalysisStatus): void {
  const statusEl = document.getElementById('analysisJobStatus')!;
  statusEl.classList.remove(...STATUS_COLOR_CLASSES);
  if (status.status === 'running') {
    const percent = (status.progress_total ?? 0) > 0
      ? Math.round(((status.progress_current ?? 0) / (status.progress_total ?? 1)) * 100) : 0;
    statusEl.textContent = t('dashboard.analysis.running', { current: status.progress_current ?? 0, total: status.progress_total ?? 0, percent });
    statusEl.classList.add('text-primary');
  } else if (status.status === 'completed') {
    statusEl.textContent = t('dashboard.analysis.completed');
    statusEl.classList.add('text-success');
  } else if (status.status === 'failed') {
    statusEl.innerHTML = t('dashboard.analysis.failed') + ' <button class="btn btn-sm" id="retryAnalysisBtn" style="margin-left: 8px; padding: 4px 10px; font-size: 0.75rem;">' + t('dashboard.analysis.retry') + '</button>';
    statusEl.classList.add('text-error');
    document.getElementById('retryAnalysisBtn')!.addEventListener('click', retryAnalysis);
  } else {
    statusEl.textContent = '';
  }
}

async function loadDateChart(): Promise<void> {
  if (!document.getElementById('dateChartContainer')) return;
  try {
    const data = await client.stats.gamesByDate(getParams()) as { items: DateChartItem[] };
    const container = document.getElementById('dateChartContainer')!;
    const emptyMsg = document.getElementById('dateChartEmpty')!;

    if (!data.items || data.items.length === 0) {
      container.classList.add('hidden');
      emptyMsg.classList.remove('hidden');
      return;
    }

    container.classList.remove('hidden');
    emptyMsg.classList.add('hidden');

    if (dateChart) dateChart.destroy();
    const ctx = (document.getElementById('dateChart') as HTMLCanvasElement).getContext('2d')!;
    dateChart = createDateChart(
      ctx,
      data.items.map(d => d.date),
      data.items.map(d => d.game_count),
      data.items.map(d => d.avg_accuracy),
    );
  } catch (err) {
    console.error('Failed to load date chart:', err);
  }
}

async function loadHourChart(): Promise<void> {
  if (!document.getElementById('hourChartContainer')) return;
  try {
    const data = await client.stats.gamesByHour(getParams()) as { items: HourChartItem[] };
    const container = document.getElementById('hourChartContainer')!;
    const emptyMsg = document.getElementById('hourChartEmpty')!;

    if (!data.items || data.items.length === 0) {
      container.classList.add('hidden');
      emptyMsg.classList.remove('hidden');
      return;
    }

    container.classList.remove('hidden');
    emptyMsg.classList.add('hidden');

    const hourMap = new Map<number, HourChartItem>(data.items.map(d => [d.hour, d]));
    const fullData: HourChartItem[] = [];
    for (let h = 0; h < 24; h++) {
      fullData.push(hourMap.get(h) || { hour: h, game_count: 0, avg_accuracy: 0 });
    }

    if (hourChart) hourChart.destroy();
    const ctx = (document.getElementById('hourChart') as HTMLCanvasElement).getContext('2d')!;
    hourChart = createHourChart(
      ctx,
      fullData.map(d => `${d.hour.toString().padStart(2, '0')}:00`),
      fullData.map(d => d.game_count),
      fullData.map(d => d.avg_accuracy),
    );
  } catch (err) {
    console.error('Failed to load hour chart:', err);
  }
}

async function retryAnalysis(): Promise<void> {
  try {
    await client.analysis.start();
    loadStats();
  } catch (err) {
    console.error('Failed to retry analysis:', err);
    alert('Failed to start analysis: ' + (err instanceof Error ? err.message : String(err)));
  }
}

async function loadStats(): Promise<void> {
  try {
    const overview = await client.stats.overview(getParams()) as OverviewData;

    document.getElementById('totalGames')!.textContent = String(overview.total_games || 0);
    document.getElementById('analyzedGames')!.textContent = String(overview.analyzed_games || 0);
    document.getElementById('totalBlunders')!.textContent = String(overview.total_blunders || 0);

    const totalGames = overview.total_games || 0;
    const analyzedGames = overview.analyzed_games || 0;
    const progressPercent = totalGames > 0 ? Math.round((analyzedGames / totalGames) * 100) : 0;
    document.getElementById('progressPercent')!.textContent = progressPercent + '%';
    (document.getElementById('progressFill') as HTMLElement).style.width = progressPercent + '%';

    const analysisStatus = await client.analysis.status() as AnalysisStatus;
    renderAnalysisStatus(analysisStatus);

    if (hasFeature('dashboard.accuracy')) {
      await loadDateChart();
      await loadHourChart();
    }

    if (hasFeature('dashboard.phase_breakdown') && document.getElementById('phaseBreakdown')) {
      const phaseData = await client.stats.blundersByPhase(getParams());
      applyBreakdown('phaseBreakdown', 'phaseBarContainer', 'phaseBar', null, renderPhaseBreakdown(phaseData as Parameters<typeof renderPhaseBreakdown>[0]));
    }

    const colorData = await client.stats.blundersByColor(getParams());
    applyBreakdown('colorBreakdown', 'colorBarContainer', 'colorBar', null, renderColorBreakdown(colorData as Parameters<typeof renderColorBreakdown>[0]));

    const gameTypeData = await client.stats.blundersByGameType(getParams());
    applyBreakdown('gameTypeBreakdown', 'gameTypeBarContainer', 'gameTypeBar', 'gameTypeLegend', renderGameTypeBreakdown(gameTypeData as Parameters<typeof renderGameTypeBreakdown>[0]));

    if (hasFeature('dashboard.opening_breakdown') && document.getElementById('ecoBreakdown')) {
      const ecoData = await client.stats.blundersByEco(getParams());
      const ecoBreakdown = document.getElementById('ecoBreakdown')!;
      ecoBreakdown.innerHTML = renderEcoBreakdown(ecoData as Parameters<typeof renderEcoBreakdown>[0]);
      initOpeningGroupToggles(ecoBreakdown);
    }

    if (hasFeature('dashboard.difficulty_breakdown') && document.getElementById('difficultyBreakdown')) {
      const diffData = await client.stats.blundersByDifficulty(getParams());
      applyBreakdown('difficultyBreakdown', 'difficultyBarContainer', 'difficultyBar', 'difficultyLegend', renderDifficultyBreakdown(diffData as Parameters<typeof renderDifficultyBreakdown>[0]));
    }

    if (hasFeature('dashboard.collapse_point') && document.getElementById('collapsePointContainer')) {
      const cpData = await client.stats.collapsePoint(getParams());
      document.getElementById('collapsePointContainer')!.innerHTML = renderCollapsePoint(cpData as Parameters<typeof renderCollapsePoint>[0]);
    }

    if (hasFeature('dashboard.conversion_resilience') && document.getElementById('conversionResilienceContainer')) {
      const crData = await client.stats.conversionResilience(getParams());
      document.getElementById('conversionResilienceContainer')!.innerHTML = renderConversionResilience(crData as Parameters<typeof renderConversionResilience>[0]);
    }

    if (hasFeature('dashboard.traps') && document.getElementById('trapsDashboardCard')) {
      try {
        const trapsData = await client.traps.stats();
        document.getElementById('trapsDashboardCard')!.innerHTML = renderTrapsSummary(trapsData as Parameters<typeof renderTrapsSummary>[0]);
      } catch {
        const card = document.getElementById('trapsDashboardCard');
        if (card) card.innerHTML = '';
      }
    }

    if (hasFeature('dashboard.growth') && document.getElementById('growthMetricsContent')) {
      await loadGrowthMetrics(getParams());
    }

    if (hasFeature('dashboard.tactical_breakdown') && document.getElementById('tacticalBreakdown')) {
      const tacticalData = await client.stats.blundersByTacticalPattern(getParams());
      applyBreakdown('tacticalBreakdown', 'tacticalBarContainer', 'tacticalBar', 'tacticalLegend', renderTacticalBreakdown(tacticalData as Parameters<typeof renderTacticalBreakdown>[0]));
    }

    const breakdown = await client.stats.gameBreakdown() as { items?: Parameters<typeof renderGameBreakdown>[0] };
    document.querySelector('#gameBreakdownTable tbody')!.innerHTML = renderGameBreakdown(breakdown.items || []);
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// --- Init ---

currentGameTypeFilters = gameTypeFilter.load();
currentGamePhaseFilters = gamePhaseFilter.load();
initDateFilters();

document.querySelectorAll<HTMLInputElement>('.game-type-filter').forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentGameTypeFilters = gameTypeFilter.save();
    loadStats();
  });
});

document.querySelectorAll<HTMLInputElement>('.game-phase-filter').forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentGamePhaseFilters = gamePhaseFilter.save();
    loadStats();
  });
});

bus.on('dashboard:reload', loadStats);

loadStats();

if (hasFeature('dashboard.heatmap')) {
  trackEvent('Heatmap Opened');
  loadHeatmap('activityHeatmap');
}

// Difficulty help modal
const diffHelpBtn = document.getElementById('difficultyHelpBtn');
const diffHelpOverlay = document.getElementById('difficultyHelpOverlay');
const diffHelpClose = document.getElementById('difficultyHelpClose');

if (diffHelpBtn && diffHelpOverlay) {
  diffHelpBtn.addEventListener('click', () => diffHelpOverlay.classList.add('visible'));
  diffHelpClose?.addEventListener('click', () => diffHelpOverlay.classList.remove('visible'));
  diffHelpOverlay.addEventListener('click', (e) => {
    if (e.target === diffHelpOverlay) diffHelpOverlay.classList.remove('visible');
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && diffHelpOverlay.classList.contains('visible')) {
      diffHelpOverlay.classList.remove('visible');
    }
  });
}

// WebSocket
wsClient.connect();
wsClient.subscribe(['stats.updated', 'job.completed', 'job.progress_updated', 'job.status_changed']);

const debouncedLoadStats = debounce(loadStats, 2000);

wsClient.on('stats.updated', () => loadStats());
wsClient.on('job.completed', () => loadStats());
wsClient.on('job.progress_updated', () => debouncedLoadStats());
wsClient.on('job.status_changed', () => loadStats());
