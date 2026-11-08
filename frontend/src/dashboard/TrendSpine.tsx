import type { ComponentChildren } from 'preact';
import { useState } from 'preact/hooks';
import { Tabs } from '../components/layout/Tabs';
import { Sparkline } from '../components/data/Sparkline';
import { InfoModal } from './InfoModal';
import type { GrowthData, GrowthWindow } from './types';

type MetricKey = keyof Pick<GrowthWindow, 'avg_blunders_per_game' | 'clean_game_rate' | 'catastrophic_rate' | 'avg_blunder_severity' | 'avg_cpl'>;

type Unit = 'count' | 'percent' | 'cp' | 'pawns';

interface TrendMetric {
  key: MetricKey;
  label: string;
  precision: number;
  lowerIsBetter: boolean;
  unit: Unit;
  // Smallest move between the compared ends that counts as a change, in the metric's own units.
  noise: number;
}

const BLUNDERS_PER_GAME: TrendMetric = { key: 'avg_blunders_per_game', label: 'dashboard.trend.tab.blunders', precision: 1, lowerIsBetter: true, unit: 'count', noise: 0.1 };

const METRICS: TrendMetric[] = [
  BLUNDERS_PER_GAME,
  { key: 'clean_game_rate', label: 'dashboard.trend.tab.clean', precision: 0, lowerIsBetter: false, unit: 'percent', noise: 2 },
  { key: 'catastrophic_rate', label: 'dashboard.trend.tab.game_losing', precision: 0, lowerIsBetter: true, unit: 'percent', noise: 2 },
  { key: 'avg_blunder_severity', label: 'dashboard.trend.tab.severity', precision: 1, lowerIsBetter: true, unit: 'pawns', noise: 10 },
  { key: 'avg_cpl', label: 'dashboard.trend.tab.cpl', precision: 0, lowerIsBetter: true, unit: 'cp', noise: 5 },
];

const MAX_COMPARED_BLOCKS = 3;
// A change counts once it beats both 5% of the starting value and the metric's own noise floor.
const STABLE_TOLERANCE = 0.05;

export type TrendDirection = 'improving' | 'declining' | 'stable';

export interface EndsComparison {
  before: number;
  now: number;
  blocks: number;
  direction: TrendDirection;
}

function mean(values: (number | null)[]): number | null {
  const known = values.filter((v): v is number => v !== null);
  return known.length > 0 ? known.reduce((sum, v) => sum + v, 0) / known.length : null;
}

export function compareEnds(
  values: (number | null)[],
  { lowerIsBetter, noise }: Pick<TrendMetric, 'lowerIsBetter' | 'noise'>,
): EndsComparison | null {
  const blocks = Math.min(MAX_COMPARED_BLOCKS, Math.floor(values.length / 2));
  if (blocks < 1) return null;
  const before = mean(values.slice(0, blocks));
  const now = mean(values.slice(-blocks));
  if (before === null || now === null) return null;
  const delta = now - before;
  if (Math.abs(delta) <= Math.max(Math.abs(before) * STABLE_TOLERANCE, noise)) return { before, now, blocks, direction: 'stable' };
  return { before, now, blocks, direction: (delta < 0) === lowerIsBetter ? 'improving' : 'declining' };
}

export function niceScale(max: number): { top: number; step: number } {
  if (max <= 0) return { top: 1, step: 0.25 };
  const raw = max / 5;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find(m => m * magnitude >= raw) ?? 10) * magnitude;
  return { top: step * Math.ceil(max / step), step };
}

function format(value: number, metric: TrendMetric): string {
  const digits = { minimumFractionDigits: metric.precision, maximumFractionDigits: metric.precision };
  if (metric.unit === 'pawns') return t('dashboard.unit.pawns', { value: formatNumber(value / 100, digits) });
  if (metric.unit === 'percent') return formatNumber(value / 100, { ...digits, style: 'percent' });
  const number = formatNumber(value, digits);
  return metric.unit === 'cp' ? t('dashboard.unit.cp', { value: number }) : number;
}

function valuesOf(windows: GrowthWindow[], key: MetricKey): (number | null)[] {
  return windows.map(w => {
    const value = w[key];
    return value !== null && Number.isFinite(value) ? value : null;
  });
}

interface CompareRanges {
  firstStart: number;
  firstEnd: number;
  lastStart: number;
  lastEnd: number;
}

// Blocks are anchored on the newest game, so the oldest few games can fall outside the first block.
function compareRanges(windows: GrowthWindow[], blocks: number): CompareRanges {
  return {
    firstStart: windows[0]?.game_start ?? 0,
    firstEnd: windows[blocks - 1]?.game_end ?? 0,
    lastStart: windows[windows.length - blocks]?.game_start ?? 0,
    lastEnd: windows.at(-1)?.game_end ?? 0,
  };
}

function blockLabel(w: GrowthWindow): string {
  return t('growth.window_label', { start: w.game_start, end: w.game_end });
}

interface BlockChartProps {
  windows: GrowthWindow[];
  values: (number | null)[];
  comparison: EndsComparison;
  metric: TrendMetric;
  ranges: CompareRanges;
  verdict: string;
}

function BlockChart({ windows, values, comparison, metric, ranges, verdict }: BlockChartProps) {
  const known = values.filter((v): v is number => v !== null);
  const { top, step } = niceScale(Math.max(...known, comparison.before, comparison.now));
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
  const pct = (v: number) => `${String((v / top) * 100)}%`;
  const span = `${String((comparison.blocks / values.length) * 100)}%`;
  const labelEvery = Math.ceil(values.length / 8);

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
            if (!w || value === null) return <span key={w?.window_index ?? i} class="trend-chart__bar trend-chart__bar--empty" />;
            return (
              <span
                key={w.window_index}
                class={`trend-chart__bar trend-chart__bar--${role}`}
                style={{ height: pct(value) }}
                title={`${blockLabel(w)}: ${format(value, metric)}`}
              />
            );
          })}
        </div>
        <span class="trend-chart__ref trend-chart__ref--first" style={{ bottom: pct(comparison.before), left: 0, width: span }}>
          <span>{ranges.firstStart}–{ranges.firstEnd} · {format(comparison.before, metric)}</span>
        </span>
        <span class={`trend-chart__ref trend-chart__ref--last trend--${comparison.direction}`} style={{ bottom: pct(comparison.now), right: 0, width: span }}>
          <span>{ranges.lastStart}–{ranges.lastEnd} · {format(comparison.now, metric)}</span>
        </span>
      </div>
      <div class="trend-chart__axis" aria-hidden="true">
        {windows.map((w, i) => <span key={w.window_index}>{i % labelEvery === 0 ? formatNumber(w.game_start) : ''}</span>)}
      </div>
      {/* Table elements ignore the 1px box, so the wrapper carries the hiding. */}
      <div class="sr-only">
        <table>
          <caption>{t(metric.label)}</caption>
          <tbody>
            {windows.map((w, i) => {
              const value = values[i];
              return (
                <tr key={w.window_index}>
                  <th scope="row">{blockLabel(w)}</th>
                  <td>{value === null || value === undefined ? '—' : format(value, metric)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
  const comparison = compareEnds(values, metric);
  const ranges = comparison ? compareRanges(growth.windows, comparison.blocks) : null;
  const rangesLabel = ranges ? t('dashboard.trend.compare_ranges', { ...ranges }) : '';
  const verdict = comparison ? t(`dashboard.trend.verdict.${comparison.direction}`) : '';
  const cplHelp = (
    <button type="button" class="info-help-btn" aria-label={t('growth.cpl_help_label')} onClick={() => { setCplHelpOpen(true); }}>?</button>
  );

  return (
    <section class="trend-spine" aria-label={t('dashboard.chart.growth')}>
      <div class="trend-spine__main">
        <Tabs
          tabs={METRICS.map(m => ({ key: m.key, label: t(m.label) }))}
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
                  {rangesLabel}
                </span>
              </p>
              <BlockChart windows={growth.windows} values={values} comparison={comparison} metric={metric} ranges={compareRanges(growth.windows, comparison.blocks)} verdict={verdict} />
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
            <h3 class="trend-side__title">{rangesLabel}</h3>
            <ul class="trend-side__list">
              {METRICS.filter(m => m.key !== selected).map(m => {
                const series = valuesOf(growth.windows, m.key);
                const ends = compareEnds(series, m);
                if (!ends) return null;
                return (
                  <li key={m.key} class="trend-side__row" data-metric={m.key}>
                    <span class="trend-side__label">{t(m.label)}{m.key === 'avg_cpl' && cplHelp}</span>
                    <span class="trend-side__values">{format(ends.before, m)} → {format(ends.now, m)}</span>
                    <span class="trend-side__spark" aria-hidden="true"><Sparkline values={series.filter((v): v is number => v !== null)} width={96} height={28} /></span>
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
