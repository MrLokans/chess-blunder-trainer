import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { client } from '../shared/api';
import { useFeature } from '../hooks/useFeature';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAsyncData } from '../hooks/useAsyncData';
import { AsyncBoundary } from '../components/feedback/AsyncBoundary';
import { debounce } from '../shared/debounce';
import { useDashboardFilters } from './useDashboardFilters';
import { DashboardFilters } from './DashboardFilters';
import { StatsOverview } from './StatsOverview';
import { ChartPanel } from './ChartPanel';
import { BreakdownSection } from './BreakdownSection';
import { InfoModal } from './InfoModal';
import { GrowthMetrics } from './GrowthMetrics';
import { createDateChart, createHourChart } from './charts';
import { ActivityHeatmap } from './ActivityHeatmap';
import {
  PhaseBreakdown,
  ColorBreakdown,
  GameTypeBreakdown,
  EcoBreakdown,
  TacticalBreakdown,
  DifficultyBreakdown,
  CollapsePointBreakdown,
  ConversionResilienceBreakdown,
  TrapsSummary,
  GameBreakdownTable,
} from './breakdowns';
import type {
  DateFilterParams,
  OverviewData,
  AnalysisStatus,
  DateChartItem,
  HourChartItem,
  PhaseData,
  ColorData,
  GameTypeData,
  EcoData,
  TacticalData,
  DifficultyData,
  CollapsePointData,
  ConversionResilienceData,
  GameBreakdownItem,
} from './types';
import type { TrapStatsResponse } from '../types/api';

interface DashboardData {
  overview: OverviewData;
  analysisStatus: AnalysisStatus;
  dateItems: DateChartItem[] | null;
  hourItems: HourChartItem[] | null;
  phaseData: PhaseData | null;
  colorData: ColorData | null;
  gameTypeData: GameTypeData | null;
  ecoData: EcoData | null;
  tacticalData: TacticalData | null;
  difficultyData: DifficultyData | null;
  collapseData: CollapsePointData | null;
  conversionData: ConversionResilienceData | null;
  trapsData: TrapStatsResponse | null;
  gameBreakdown: GameBreakdownItem[] | null;
}

interface DashboardFeatures {
  hasAccuracy: boolean;
  hasPhase: boolean;
  hasOpening: boolean;
  hasDifficulty: boolean;
  hasTactical: boolean;
  hasCollapse: boolean;
  hasConversion: boolean;
  hasTraps: boolean;
  hasGrowth: boolean;
  hasHeatmap: boolean;
}

function toQueryParams(params: DateFilterParams): Record<string, string | string[] | undefined> {
  return { ...params };
}

function fillHours(items: HourChartItem[]): HourChartItem[] {
  const hourMap = new Map<number, HourChartItem>(items.map(d => [d.hour, d]));
  const result: HourChartItem[] = [];
  for (let h = 0; h < 24; h++) {
    result.push(hourMap.get(h) ?? { hour: h, game_count: 0, avg_accuracy: 0 });
  }
  return result;
}

export function DashboardApp() {
  const [difficultyHelpOpen, setDifficultyHelpOpen] = useState(false);

  const filters = useDashboardFilters();
  const features: DashboardFeatures = {
    hasAccuracy: useFeature('dashboard.accuracy'),
    hasPhase: useFeature('dashboard.phase_breakdown'),
    hasOpening: useFeature('dashboard.opening_breakdown'),
    hasDifficulty: useFeature('dashboard.difficulty_breakdown'),
    hasTactical: useFeature('dashboard.tactical_breakdown'),
    hasCollapse: useFeature('dashboard.collapse_point'),
    hasConversion: useFeature('dashboard.conversion_resilience'),
    hasTraps: useFeature('dashboard.traps'),
    hasGrowth: useFeature('dashboard.growth'),
    hasHeatmap: useFeature('dashboard.heatmap'),
  };

  const ws = useWebSocket(['stats.updated', 'job.completed', 'job.progress_updated', 'job.status_changed']);

  const getParams = filters.getParams;
  const { hasAccuracy, hasPhase, hasOpening, hasDifficulty, hasTactical, hasCollapse, hasConversion, hasTraps } = features;

  const state = useAsyncData<DashboardData>(
    async (): Promise<DashboardData> => {
      const qp = toQueryParams(getParams());

      const [overview, analysisStatus, gameBreakdownResp] = await Promise.all([
        client.stats.overview(qp),
        client.analysis.status(),
        client.stats.gameBreakdown(),
      ]);

      const [
        dateResp,
        hourResp,
        phaseData,
        colorData,
        gameTypeData,
        ecoData,
        difficultyData,
        tacticalData,
        collapseData,
        conversionData,
        trapsResp,
      ] = await Promise.all([
        hasAccuracy ? client.stats.gamesByDate(qp) : Promise.resolve(null),
        hasAccuracy ? client.stats.gamesByHour(qp) : Promise.resolve(null),
        hasPhase ? client.stats.blundersByPhase(qp) : Promise.resolve(null),
        client.stats.blundersByColor(qp),
        client.stats.blundersByGameType(qp),
        hasOpening ? client.stats.blundersByEco(qp) : Promise.resolve(null),
        hasDifficulty ? client.stats.blundersByDifficulty(qp) : Promise.resolve(null),
        hasTactical ? client.stats.blundersByTacticalPattern(qp) : Promise.resolve(null),
        hasCollapse ? client.stats.collapsePoint(qp) : Promise.resolve(null),
        hasConversion ? client.stats.conversionResilience(qp) : Promise.resolve(null),
        hasTraps ? client.traps.stats() : Promise.resolve(null),
      ] as const);

      return {
        overview,
        analysisStatus,
        dateItems: dateResp?.items ?? null,
        hourItems: hourResp?.items ?? null,
        phaseData: phaseData ?? null,
        colorData,
        gameTypeData,
        ecoData: ecoData ?? null,
        difficultyData: difficultyData ?? null,
        tacticalData: tacticalData ?? null,
        collapseData: collapseData ?? null,
        conversionData: conversionData ?? null,
        trapsData: trapsResp ?? null,
        gameBreakdown: gameBreakdownResp.items,
      };
    },
    [getParams, hasAccuracy, hasPhase, hasOpening, hasDifficulty, hasTactical, hasCollapse, hasConversion, hasTraps],
  );

  const reload = state.reload;
  const debouncedReload = useMemo(() => debounce(reload, 2000), [reload]);

  useEffect(() => {
    const unsub1 = ws.on('stats.updated', () => { reload(); });
    const unsub2 = ws.on('job.completed', () => { reload(); });
    const unsub3 = ws.on('job.progress_updated', () => { debouncedReload(); });
    const unsub4 = ws.on('job.status_changed', () => { reload(); });
    return () => { unsub1(); unsub2(); unsub3(); unsub4(); };
  }, [ws, reload, debouncedReload]);

  const handleRetryAnalysis = useCallback(async () => {
    try {
      await client.analysis.start();
      reload();
    } catch (err) {
      console.error('Failed to retry analysis:', err);
    }
  }, [reload]);

  return (
    <AsyncBoundary state={state} isEmpty={() => false}>
      {(data) => (
        <DashboardBody
          data={data}
          features={features}
          filters={filters}
          getParams={getParams}
          difficultyHelpOpen={difficultyHelpOpen}
          setDifficultyHelpOpen={setDifficultyHelpOpen}
          onRetryAnalysis={() => { void handleRetryAnalysis(); }}
        />
      )}
    </AsyncBoundary>
  );
}

interface DashboardBodyProps {
  data: DashboardData;
  features: DashboardFeatures;
  filters: ReturnType<typeof useDashboardFilters>;
  getParams: () => DateFilterParams;
  difficultyHelpOpen: boolean;
  setDifficultyHelpOpen: (open: boolean) => void;
  onRetryAnalysis: () => void;
}

function DashboardBody({
  data: state,
  features,
  filters,
  getParams,
  difficultyHelpOpen,
  setDifficultyHelpOpen,
  onRetryAnalysis,
}: DashboardBodyProps) {
  const {
    hasAccuracy, hasPhase, hasOpening, hasDifficulty, hasTactical,
    hasCollapse, hasConversion, hasTraps, hasGrowth, hasHeatmap,
  } = features;

  const dateChartData = state.dateItems && state.dateItems.length > 0 ? {
    labels: state.dateItems.map(d => d.date),
    gameCounts: state.dateItems.map(d => d.game_count),
    accuracies: state.dateItems.map(d => d.avg_accuracy),
  } : null;

  const filledHours = state.hourItems ? fillHours(state.hourItems) : null;
  const hourChartData = filledHours && filledHours.some(h => h.game_count > 0) ? {
    labels: filledHours.map(d => `${String(d.hour).padStart(2, '0')}:00`),
    gameCounts: filledHours.map(d => d.game_count),
    accuracies: filledHours.map(d => d.avg_accuracy),
  } : null;

  return (
    <>
      <DashboardFilters
        datePreset={filters.datePreset}
        dateFrom={filters.dateFrom}
        dateTo={filters.dateTo}
        gameTypes={filters.gameTypes}
        gamePhases={filters.gamePhases}
        onDatePreset={filters.setDatePreset}
        onCustomDateRange={filters.setCustomDateRange}
        onClearDate={filters.clearDateFilter}
        onGameTypesChange={filters.setGameTypes}
        onGamePhasesChange={filters.setGamePhases}
      />

      <StatsOverview
        totalGames={state.overview.total_games}
        analyzedGames={state.overview.analyzed_games}
        totalBlunders={state.overview.total_blunders}
        analysisStatus={state.analysisStatus}
        onRetryAnalysis={onRetryAnalysis}
      />

      {hasGrowth && (
        <BreakdownSection
          title={t('dashboard.chart.growth')}
          description={t('dashboard.chart.growth_desc')}
        >
          <GrowthMetrics params={toQueryParams(getParams())} />
        </BreakdownSection>
      )}

      {hasAccuracy && (
        <ChartPanel
          title={t('dashboard.chart.accuracy_by_date')}
          description={t('dashboard.chart.accuracy_by_date_desc')}
          emptyMessage={t('dashboard.chart.no_accuracy_data')}
          data={dateChartData}
          createChart={createDateChart}
        />
      )}

      {hasCollapse && state.collapseData && (
        <BreakdownSection
          title={t('dashboard.chart.collapse_point')}
          description={t('dashboard.chart.collapse_point_desc')}
        >
          <CollapsePointBreakdown data={state.collapseData} />
        </BreakdownSection>
      )}

      {hasTactical && state.tacticalData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_tactical')}
          description={t('dashboard.chart.blunders_by_tactical_desc')}
        >
          <TacticalBreakdown data={state.tacticalData} />
        </BreakdownSection>
      )}

      {hasPhase && state.phaseData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_phase')}
          description={t('dashboard.chart.blunders_by_phase_desc')}
        >
          <PhaseBreakdown data={state.phaseData} />
        </BreakdownSection>
      )}

      {hasConversion && state.conversionData && (
        <BreakdownSection
          title={t('dashboard.chart.conversion_resilience')}
          description={t('dashboard.chart.conversion_resilience_desc')}
        >
          <ConversionResilienceBreakdown data={state.conversionData} />
        </BreakdownSection>
      )}

      {hasHeatmap && (
        <BreakdownSection
          title={t('dashboard.chart.puzzle_activity')}
          description={t('dashboard.chart.puzzle_activity_desc')}
        >
          <ActivityHeatmap />
        </BreakdownSection>
      )}

      {hasOpening && state.ecoData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_opening')}
          description={t('dashboard.chart.blunders_by_opening_desc')}
        >
          <EcoBreakdown data={state.ecoData} />
        </BreakdownSection>
      )}

      {hasDifficulty && state.difficultyData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_difficulty')}
          description={t('dashboard.chart.blunders_by_difficulty_desc')}
          helpButton={
            <button
              class="info-help-btn"
              aria-label={t('dashboard.difficulty.help_label')}
              onClick={() => { setDifficultyHelpOpen(true); }}
            >
              ?
            </button>
          }
        >
          <DifficultyBreakdown data={state.difficultyData} />
        </BreakdownSection>
      )}

      {state.colorData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_color')}
          description={t('dashboard.chart.blunders_by_color_desc')}
        >
          <ColorBreakdown data={state.colorData} />
        </BreakdownSection>
      )}

      {state.gameTypeData && (
        <BreakdownSection
          title={t('dashboard.chart.blunders_by_game_type')}
          description={t('dashboard.chart.blunders_by_game_type_desc')}
        >
          <GameTypeBreakdown data={state.gameTypeData} />
        </BreakdownSection>
      )}

      {hasTraps && state.trapsData && (
        <BreakdownSection
          title={t('traps.dashboard_card_title')}
          description={t('traps.dashboard_card_desc')}
        >
          <TrapsSummary data={state.trapsData} />
        </BreakdownSection>
      )}

      {hasAccuracy && (
        <ChartPanel
          title={t('dashboard.chart.accuracy_by_hour')}
          description={t('dashboard.chart.accuracy_by_hour_desc')}
          emptyMessage={t('dashboard.chart.no_hourly_data')}
          data={hourChartData}
          createChart={createHourChart}
        />
      )}

      <div class="chart-container">
        <div class="chart-title">{t('dashboard.chart.game_breakdown')}</div>
        <GameBreakdownTable items={state.gameBreakdown ?? []} />
      </div>

      <div class="mt-4">
        <a class="btn" href="/management">{t('dashboard.link.manage_imports')}</a>
      </div>

      <InfoModal
        open={difficultyHelpOpen}
        onClose={() => { setDifficultyHelpOpen(false); }}
        title={t('dashboard.difficulty.help_title')}
      >
        <p>{t('dashboard.difficulty.help_intro')}</p>
        <dl class="info-modal-definitions">
          <dt class="diff-easy">{t('dashboard.difficulty.easy')} (0-30)</dt>
          <dd>{t('dashboard.difficulty.help_easy')}</dd>
          <dt class="diff-medium">{t('dashboard.difficulty.medium')} (31-60)</dt>
          <dd>{t('dashboard.difficulty.help_medium')}</dd>
          <dt class="diff-hard">{t('dashboard.difficulty.hard')} (61-100)</dt>
          <dd>{t('dashboard.difficulty.help_hard')}</dd>
        </dl>
        <p class="info-modal-note">{t('dashboard.difficulty.help_factors')}</p>
      </InfoModal>

    </>
  );
}
