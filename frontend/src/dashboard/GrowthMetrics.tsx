import { useState, useEffect } from 'preact/hooks';
import { client } from '../shared/api';
import { InfoModal } from './InfoModal';
import type { GrowthData } from './types';

interface GrowthMetric {
  key: string;
  i18n: string;
  trendKey: string;
  precision: number;
  lowerIsBetter: boolean;
  suffix?: string;
  helpBtnId?: string;
}

const METRICS: GrowthMetric[] = [
  { key: 'avg_blunders_per_game', i18n: 'growth.blunders_per_game', trendKey: 'blunder_frequency', precision: 2, lowerIsBetter: true },
  { key: 'avg_cpl',              i18n: 'growth.avg_cpl',            trendKey: 'move_quality',       precision: 1, lowerIsBetter: true, helpBtnId: 'cplHelpBtn' },
  { key: 'avg_blunder_severity', i18n: 'growth.blunder_severity',   trendKey: 'severity',           precision: 1, lowerIsBetter: true },
  { key: 'clean_game_rate',      i18n: 'growth.clean_game_rate',    trendKey: 'clean_rate',         precision: 1, lowerIsBetter: false, suffix: '%' },
  { key: 'catastrophic_rate',    i18n: 'growth.catastrophic_rate',  trendKey: 'catastrophic_rate',  precision: 1, lowerIsBetter: true,  suffix: '%' },
];

type QueryParams = Record<string, string | number | boolean | null | undefined | string[]>;

interface SparklineProps {
  values: number[];
}

function Sparkline({ values }: SparklineProps) {
  if (values.length < 2) return null;

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

  return (
    <svg class="growth-sparkline" viewBox={`0 0 ${String(width)} ${String(height)}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke="var(--primary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  );
}

interface TrendArrowProps {
  direction: string | null;
  lowerIsBetter: boolean;
}

function TrendArrow({ direction, lowerIsBetter }: TrendArrowProps) {
  if (!direction || direction === 'stable') {
    if (direction === 'stable') {
      return <span class="growth-trend growth-trend--stable" title={t('growth.stable')}>{'\u2192'}</span>;
    }
    return null;
  }

  const valueWentDown = (direction === 'improving') === lowerIsBetter;
  const symbol = valueWentDown ? '\u2193' : '\u2191';
  const isGood = direction === 'improving';
  const cssClass = isGood ? 'growth-trend--improving' : 'growth-trend--declining';
  const label = t('growth.' + direction);

  return <span class={`growth-trend ${cssClass}`} title={label}>{symbol}</span>;
}

interface GrowthMetricsProps {
  params?: QueryParams;
}

export function GrowthMetrics({ params }: GrowthMetricsProps) {
  const [data, setData] = useState<GrowthData | null>(null);
  const [cplHelpOpen, setCplHelpOpen] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    setData(null);
    setError(false);
    void (async () => {
      try {
        const result = await client.stats.growth(params);
        setData(result);
      } catch (err) {
        console.error('Failed to load growth metrics:', err);
        setError(true);
      }
    })();
  }, [params]);

  if (error) return <div class="no-data-message">{t('growth.load_error')}</div>;

  if (!data) {
    return <div class="loading-placeholder">{t('common.loading')}</div>;
  }

  if (data.total_games === 0) {
    return <div class="no-data-message">{t('growth.no_data')}</div>;
  }

  if (data.windows.length === 0) {
    return <div class="no-data-message">{t('growth.insufficient_data', { count: data.window_size })}</div>;
  }

  return (
    <>
      {METRICS.map(metric => {
        const values = data.windows.map(w => w[metric.key] ?? 0);
        const current = values[values.length - 1]!;
        const suffix = metric.suffix ?? '';
        const trendDir = metric.trendKey && data.trend ? (data.trend[metric.trendKey] ?? null) : null;

        return (
          <div key={metric.key} class="growth-metric-row">
            <span class="growth-metric-label">
              {t(metric.i18n)}
              {metric.helpBtnId && (
                <button
                  class="info-help-btn"
                  id={metric.helpBtnId}
                  aria-label={t('growth.cpl_help_label')}
                  onClick={() => { setCplHelpOpen(true); }}
                >
                  ?
                </button>
              )}
            </span>
            <Sparkline values={values} />
            <span class="growth-value">{current.toFixed(metric.precision)}{suffix}</span>
            <TrendArrow direction={trendDir} lowerIsBetter={metric.lowerIsBetter} />
          </div>
        );
      })}

      {data.windows.length < 2 && (
        <div class="growth-insufficient">{t('growth.insufficient_data', { count: data.window_size * 2 })}</div>
      )}

      <InfoModal
        open={cplHelpOpen}
        onClose={() => { setCplHelpOpen(false); }}
        title={t('growth.cpl_help_title')}
      >
        <p>{t('growth.cpl_help_intro')}</p>
        <h4>{t('growth.cpl_help_scale_title')}</h4>
        <dl class="info-modal-definitions">
          <dt>{'< 50'}</dt>
          <dd>{t('growth.cpl_help_excellent')}</dd>
          <dt>50–100</dt>
          <dd>{t('growth.cpl_help_good')}</dd>
          <dt>100–150</dt>
          <dd>{t('growth.cpl_help_average')}</dd>
          <dt>{'> 150'}</dt>
          <dd>{t('growth.cpl_help_high')}</dd>
        </dl>
        <p class="info-modal-note">{t('growth.cpl_help_note')}</p>
      </InfoModal>
    </>
  );
}
