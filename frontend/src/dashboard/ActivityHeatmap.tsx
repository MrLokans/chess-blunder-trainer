import { useState, useEffect } from 'preact/hooks';
import { client } from '../shared/api';
import type { HeatmapData } from './types';

const DAY_KEYS = [
  'common.day.sun', 'common.day.mon', 'common.day.tue', 'common.day.wed',
  'common.day.thu', 'common.day.fri', 'common.day.sat',
];
const MONTH_KEYS = [
  'common.month.jan', 'common.month.feb', 'common.month.mar', 'common.month.apr',
  'common.month.may', 'common.month.jun', 'common.month.jul', 'common.month.aug',
  'common.month.sep', 'common.month.oct', 'common.month.nov', 'common.month.dec',
];

const ACTIVITY_THRESHOLDS = {
  L2: 5,
  L3: 10,
  L4: 20,
};

function getActivityLevel(count: number): number {
  if (count === 0) return 0;
  if (count < ACTIVITY_THRESHOLDS.L2) return 1;
  if (count < ACTIVITY_THRESHOLDS.L3) return 2;
  if (count < ACTIVITY_THRESHOLDS.L4) return 3;
  return 4;
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0] ?? '';
}

interface DayData {
  date: string;
  total: number;
  correct: number;
  incorrect: number;
  level: number;
  isPast: boolean;
  dayOfWeek: number;
  month: number;
  dayOfMonth: number;
}

function buildWeeks(data: HeatmapData): { weeks: DayData[][], monthLabels: Array<{ weekIndex: number; month: string }> } {
  const { daily_counts } = data;

  const today = new Date();
  const todayStr = formatDate(today);
  const year = today.getFullYear();

  const startDate = new Date(year, 0, 1);
  while (startDate.getDay() !== 0) {
    startDate.setDate(startDate.getDate() - 1);
  }
  const endDate = new Date(year, 11, 31);
  while (endDate.getDay() !== 6) {
    endDate.setDate(endDate.getDate() + 1);
  }

  const weeks: DayData[][] = [];
  const currentDate = new Date(startDate);
  let currentWeek: DayData[] = [];

  while (currentDate <= endDate) {
    const dateStr = formatDate(currentDate);
    const dayData = daily_counts[dateStr] ?? { total: 0, correct: 0, incorrect: 0 };
    const level = getActivityLevel(dayData.total);
    const isPast = dateStr <= todayStr;

    currentWeek.push({
      date: dateStr,
      total: dayData.total,
      correct: dayData.correct,
      incorrect: dayData.incorrect,
      level,
      isPast,
      dayOfWeek: currentDate.getDay(),
      month: currentDate.getMonth(),
      dayOfMonth: currentDate.getDate(),
    });

    if (currentDate.getDay() === 6) {
      weeks.push(currentWeek);
      currentWeek = [];
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  if (currentWeek.length > 0) {
    weeks.push(currentWeek);
  }

  const monthLabels: Array<{ weekIndex: number; month: string }> = [];
  let lastMonth = -1;
  weeks.forEach((week, weekIndex) => {
    const firstDay = week[0];
    if (firstDay && firstDay.month !== lastMonth && firstDay.dayOfMonth <= 7) {
      monthLabels.push({ weekIndex, month: t(MONTH_KEYS[firstDay.month] ?? '') });
      lastMonth = firstDay.month;
    }
  });

  return { weeks, monthLabels };
}

interface HeatmapGridProps {
  data: HeatmapData;
}

function HeatmapGrid({ data }: HeatmapGridProps) {
  const { weeks, monthLabels } = buildWeeks(data);
  const { total_days, total_attempts } = data;

  return (
    <div class="heatmap-wrapper">
      <div class="heatmap-summary">
        <span class="heatmap-total">{t('heatmap.total', { count: total_attempts })}</span>
        <span class="heatmap-days">{t('heatmap.days', { count: total_days })}</span>
      </div>
      <div class="heatmap-container">
        <div class="heatmap-days-labels">
          {DAY_KEYS.filter((_, i) => i % 2 === 1).map(d => (
            <span key={d}>{t(d)}</span>
          ))}
        </div>
        <div class="heatmap-grid-wrapper">
          <div
            class="heatmap-months"
            style={{ gridTemplateColumns: `repeat(${String(weeks.length)}, 1fr)` }}
          >
            {monthLabels.map(m => (
              <span key={m.weekIndex} style={{ gridColumn: String(m.weekIndex + 1) }}>{m.month}</span>
            ))}
          </div>
          <div
            class="heatmap-grid"
            style={{ gridTemplateColumns: `repeat(${String(weeks.length)}, 1fr)` }}
          >
            {weeks.map((week, wi) => (
              <div key={wi} class="heatmap-week">
                {Array.from({ length: 7 }, (_, dayIndex) => {
                  const day = week.find(d => d.dayOfWeek === dayIndex);
                  if (!day) return <div key={dayIndex} class="heatmap-cell empty" />;
                  const tooltip = day.total === 0
                    ? t('common.no_activity', { date: day.date })
                    : t('heatmap.tooltip', { date: day.date, total: day.total, correct: day.correct, incorrect: day.incorrect });
                  const futureClass = day.level === 0 && !day.isPast ? ' future' : '';
                  return (
                    <div
                      key={dayIndex}
                      class={`heatmap-cell level-${String(day.level)}${futureClass}`}
                      data-tooltip={tooltip}
                      data-date={day.date}
                      data-total={String(day.total)}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div class="heatmap-legend">
        <span>{t('common.less')}</span>
        <div class="heatmap-cell level-0" />
        <div class="heatmap-cell level-1" />
        <div class="heatmap-cell level-2" />
        <div class="heatmap-cell level-3" />
        <div class="heatmap-cell level-4" />
        <span>{t('common.more')}</span>
      </div>
    </div>
  );
}

export function ActivityHeatmap() {
  const [data, setData] = useState<HeatmapData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    client.stats.activityHeatmap().then(result => {
      setData(result);
    }).catch((err: unknown) => {
      console.error('Failed to load heatmap:', err);
      setError(err instanceof Error ? err.message : String(err));
    });
  }, []);

  if (error !== null) {
    return <div class="heatmap-error">{t('heatmap.error')}</div>;
  }

  if (data === null) {
    return <div class="loading-placeholder">{t('dashboard.chart.loading_activity')}</div>;
  }

  return <HeatmapGrid data={data} />;
}
