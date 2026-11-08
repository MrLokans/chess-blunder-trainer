import type { ComponentChildren } from 'preact';
import { useState } from 'preact/hooks';
import { Tabs } from '../components/layout/Tabs';
import { Sparkline } from '../components/data/Sparkline';
import { InfoModal } from './InfoModal';
import type { GrowthData, GrowthWindow } from './types';

type MetricKey = keyof Pick<GrowthWindow, 'avg_blunders_per_game' | 'clean_game_rate' | 'catastrophic_rate' | 'avg_blunder_severity' | 'avg_cpl'>;

interface TrendMetric {
  key: MetricKey;
  tab: string;
  label: string;
  precision: number;
  lowerIsBetter: boolean;
  suffix: string;
}

const BLUNDERS_PER_GAME: TrendMetric = { key: 'avg_blunders_per_game', tab: 'dashboard.trend.tab.blunders', label: 'growth.blunders_per_game', precision: 1, lowerIsBetter: true, suffix: '' };

const METRICS: TrendMetric[] = [
  BLUNDERS_PER_GAME,
  { key: 'clean_game_rate', tab: 'dashboard.trend.tab.clean', label: 'growth.clean_game_rate', precision: 0, lowerIsBetter: false, suffix: '%' },
  { key: 'catastrophic_rate', tab: 'dashboard.trend.tab.game_losing', label: 'growth.catastrophic_rate', precision: 0, lowerIsBetter: true, suffix: '%' },
  { key: 'avg_blunder_severity', tab: 'dashboard.trend.tab.severity', label: 'growth.blunder_severity', precision: 0, lowerIsBetter: true, suffix: ' CP' },
  { key: 'avg_cpl', tab: 'dashboard.trend.tab.cpl', label: 'growth.avg_cpl', precision: 0, lowerIsBetter: true, suffix: ' CP' },
];

const MAX_COMPARED_BLOCKS = 3;
// Changes within 5% of the starting value read as noise between 20-game blocks.
const STABLE_TOLERANCE = 0.05;

export type TrendDirection = 'improving' | 'declining' | 'stable';

export interface EndsComparison {
  before: number;
  now: number;
  blocks: number;
  direction: TrendDirection;
}

function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

export function compareEnds(values: number[], lowerIsBetter: boolean): EndsComparison | null {
  const blocks = Math.min(MAX_COMPARED_BLOCKS, Math.floor(values.length / 2));
  if (blocks < 1) return null;
  const before = mean(values.slice(0, blocks));
  const now = mean(values.slice(-blocks));
  const change = (now - before) / Math.max(Math.abs(before), 1);
  if (Math.abs(change) <= STABLE_TOLERANCE) return { before, now, blocks, direction: 'stable' };
  return { before, now, blocks, direction: (change < 0) === lowerIsBetter ? 'improving' : 'declining' };
}

export function niceScale(max: number): { top: number; step: number } {
  if (max <= 0) return { top: 1, step: 0.25 };
  const raw = max / 5;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find(m => m * magnitude >= raw) ?? 10) * magnitude;
  return { top: step * Math.ceil(max / step), step };
}

function format(value: number, metric: TrendMetric): string {
  return `${formatNumber(value, { minimumFractionDigits: metric.precision, maximumFractionDigits: metric.precision })}${metric.suffix}`;
}

function valuesOf(windows: GrowthWindow[], key: MetricKey): number[] {
  return windows.map(w => (Number.isFinite(w[key]) ? w[key] : 0));
}

interface BlockChartProps {
  windows: GrowthWindow[];
  values: number[];
  comparison: EndsComparison;
  metric: TrendMetric;
  games: number;
  verdict: string;
}

function BlockChart({ windows, values, comparison, metric, games, verdict }: BlockChartProps) {
  const { top, step } = niceScale(Math.max(...values, comparison.before, comparison.now));
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
  const pct = (v: number) => `${String((v / top) * 100)}%`;
  const span = `${String((comparison.blocks / values.length) * 100)}%`;
  const labelEvery = values.length > 10 ? 2 : 1;

  return (
    <figure class="trend-chart">
      <div
        class="trend-chart__plot"
        role="img"
        aria-label={`${verdict}. ${t(metric.label)}: ${format(comparison.before, metric)} → ${format(comparison.now, metric)}`}
      >
        {ticks.map(tick => (
          <span key={tick} class="trend-chart__tick" style={{ bottom: pct(tick) }}>
            <span>{formatNumber(tick)}</span>
          </span>
        ))}
        <div class="trend-chart__bars">
          {values.map((value, i) => {
            const w = windows[i];
            const role = i < comparison.blocks ? 'first' : i >= values.length - comparison.blocks ? 'last' : 'middle';
            return (
              <span
                key={w?.window_index ?? i}
                class={`trend-chart__bar trend-chart__bar--${role}`}
                style={{ height: pct(value) }}
                title={`${t('growth.window_label', { start: w?.game_start ?? 0, end: w?.game_end ?? 0 })}: ${format(value, metric)}`}
              />
            );
          })}
        </div>
        <span class="trend-chart__ref trend-chart__ref--first" style={{ bottom: pct(comparison.before), left: 0, width: span }}>
          <span>{t('dashboard.trend.first_n', { count: games })} · {format(comparison.before, metric)}</span>
        </span>
        <span class={`trend-chart__ref trend-chart__ref--last trend--${comparison.direction}`} style={{ bottom: pct(comparison.now), right: 0, width: span }}>
          <span>{t('dashboard.trend.last_n', { count: games })} · {format(comparison.now, metric)}</span>
        </span>
      </div>
      <div class="trend-chart__axis" aria-hidden="true">
        {windows.map((w, i) => <span key={w.window_index}>{i % labelEvery === 0 ? formatNumber(w.game_start) : ''}</span>)}
      </div>
    </figure>
  );
}

interface TrendSpineProps {
  growth: GrowthData;
  nextStep: ComponentChildren;
}

export function TrendSpine({ growth, nextStep }: TrendSpineProps) {
  const [selected, setSelected] = useState<MetricKey>(BLUNDERS_PER_GAME.key);
  const [cplHelpOpen, setCplHelpOpen] = useState(false);
  const metric = METRICS.find(m => m.key === selected) ?? BLUNDERS_PER_GAME;
  const values = valuesOf(growth.windows, metric.key);
  const comparison = compareEnds(values, metric.lowerIsBetter);
  const games = (comparison?.blocks ?? 0) * growth.window_size;
  const verdict = comparison ? t(`dashboard.trend.verdict.${comparison.direction}`) : '';
  const cplHelp = (
    <button type="button" class="info-help-btn" aria-label={t('growth.cpl_help_label')} onClick={() => { setCplHelpOpen(true); }}>?</button>
  );

  return (
    <section class="trend-spine" aria-label={t('dashboard.chart.growth')}>
      <div class="trend-spine__main">
        <Tabs
          tabs={METRICS.map(m => ({ key: m.key, label: t(m.tab) }))}
          value={selected}
          onChange={setSelected}
        >
          {comparison ? (
            <>
              <h2 class="trend-verdict">{verdict}</h2>
              <p class="trend-numbers">
                <span class="trend-numbers__value">{format(comparison.before, metric)}</span>
                <span class="trend-numbers__arrow" aria-hidden="true">→</span>
                <span class={`trend-numbers__value trend--${comparison.direction}`}>{format(comparison.now, metric)}</span>
                <span class="trend-numbers__label">
                  {t(metric.label)}
                  {metric.key === 'avg_cpl' && cplHelp}
                  <br />
                  {t('dashboard.trend.compare', { count: games })}
                </span>
              </p>
              <BlockChart windows={growth.windows} values={values} comparison={comparison} metric={metric} games={games} verdict={verdict} />
              <p class="trend-chart__note">{t('dashboard.trend.chart_note', { size: growth.window_size })}</p>
            </>
          ) : (
            <p class="trend-empty">
              {growth.total_games === 0 ? t('growth.no_data') : t('growth.insufficient_data', { count: growth.window_size * 2 })}
            </p>
          )}
        </Tabs>
      </div>

      <aside class="trend-spine__side">
        {comparison && (
          <>
            <h3 class="trend-side__title">{t('dashboard.trend.compare', { count: games })}</h3>
            <ul class="trend-side__list">
              {METRICS.filter(m => m.key !== selected).map(m => {
                const series = valuesOf(growth.windows, m.key);
                const ends = compareEnds(series, m.lowerIsBetter);
                if (!ends) return null;
                return (
                  <li key={m.key} class="trend-side__row" data-metric={m.key}>
                    <span class="trend-side__label">{t(m.label)}{m.key === 'avg_cpl' && cplHelp}</span>
                    <span class="trend-side__values">{format(ends.before, m)} → {format(ends.now, m)}</span>
                    <span class="trend-side__spark" aria-hidden="true"><Sparkline values={series} width={96} height={28} /></span>
                    <span class={`trend-side__word trend--${ends.direction}`}>{t(`growth.${ends.direction}`)}</span>
                  </li>
                );
              })}
            </ul>
          </>
        )}
        {nextStep}
      </aside>

      <InfoModal open={cplHelpOpen} onClose={() => { setCplHelpOpen(false); }} title={t('growth.cpl_help_title')}>
        <p>{t('growth.cpl_help_intro')}</p>
        <h4>{t('growth.cpl_help_scale_title')}</h4>
        <dl class="info-modal-definitions">
          <dt>{'< 50'}</dt><dd>{t('growth.cpl_help_excellent')}</dd>
          <dt>50–100</dt><dd>{t('growth.cpl_help_good')}</dd>
          <dt>100–150</dt><dd>{t('growth.cpl_help_average')}</dd>
          <dt>{'> 150'}</dt><dd>{t('growth.cpl_help_high')}</dd>
        </dl>
        <p class="info-modal-note">{t('growth.cpl_help_note')}</p>
      </InfoModal>
    </section>
  );
}
