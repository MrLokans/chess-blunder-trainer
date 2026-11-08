import { readColorToken } from '../shared/css-color';
import { prefersReducedMotion } from '../shared/motion';

interface ChartPalette {
  text: string;
  muted: string;
  border: string;
  grid: string;
  surface: string;
}

function chartPalette(): ChartPalette {
  return {
    text: readColorToken('--text', '#1A1A1A'), muted: readColorToken('--text-muted', '#706E68'),
    border: readColorToken('--border', '#B8B4AB'), grid: readColorToken('--border-subtle', '#E8E4DB'),
    surface: readColorToken('--surface-raised', '#F5F2EB'),
  };
}

function sharedChartOptions(xAxisConfig: Record<string, unknown> = {}): Record<string, unknown> {
  const colors = chartPalette();
  const font = { family: getComputedStyle(document.body).fontFamily, size: 12 };
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: prefersReducedMotion() ? false : undefined,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top', align: 'start', labels: { color: colors.text, font, boxWidth: 12, boxHeight: 12 } },
      tooltip: {
        filter: (item: { raw: unknown }) => item.raw !== null,
        backgroundColor: colors.surface,
        titleColor: colors.text,
        bodyColor: colors.text,
        borderColor: colors.border,
        borderWidth: 1,
        callbacks: {
          label(context: { dataset: { yAxisID?: string; label?: string }; raw: number | null }) {
            if (context.dataset.yAxisID === 'y1') {
              return context.raw === null ? '' : `${t('dashboard.chart.accuracy')}: ${context.raw.toFixed(1)}%`;
            }
            return `${context.dataset.label ?? ''}: ${String(context.raw)}`;
          },
        },
      },
    },
    scales: {
      x: {
        ...xAxisConfig,
        title: { ...(xAxisConfig.title as Record<string, unknown>), color: colors.text },
        ticks: { ...(xAxisConfig.ticks as Record<string, unknown>), color: colors.muted, font },
        grid: { ...(xAxisConfig.grid as Record<string, unknown>), display: false },
        border: { color: colors.text, width: 2 },
      },
      y: {
        type: 'linear', display: true, position: 'left',
        title: { display: false },
        ticks: { color: colors.muted, font },
        grid: { color: colors.grid },
        border: { display: false },
        beginAtZero: true,
      },
      y1: {
        type: 'linear', display: true, position: 'right',
        title: { display: false },
        ticks: { color: colors.muted, font },
        min: 0, max: 100,
        grid: { drawOnChartArea: false },
        border: { display: false },
      },
    },
  };
}

function datasets(labels: string[], gameCounts: number[], accuracies: number[]): ChartConfiguration['data'] {
  const colors = chartPalette();
  return {
    labels,
    datasets: [
      {
        label: t('dashboard.chart.games_played'),
        data: gameCounts,
        backgroundColor: colors.border,
        borderWidth: 0,
        yAxisID: 'y',
        order: 2,
      },
      {
        label: t('dashboard.chart.accuracy'),
        // No games in a slot means no accuracy, so the line breaks there instead of diving to zero.
        data: accuracies.map((accuracy, i) => (gameCounts[i] ? accuracy : null)),
        type: 'line',
        borderColor: colors.text,
        backgroundColor: colors.text,
        borderWidth: 2,
        fill: false,
        tension: 0,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointStyle: 'rect',
        yAxisID: 'y1',
        order: 1,
      },
    ],
  };
}

export function createDateChart(
  ctx: CanvasRenderingContext2D,
  labels: string[],
  gameCounts: number[],
  accuracies: number[],
): ChartInstance {
  return new Chart(ctx, {
    type: 'bar',
    data: datasets(labels, gameCounts, accuracies),
    options: sharedChartOptions({
      ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
    }),
  });
}

export function createHourChart(
  ctx: CanvasRenderingContext2D,
  labels: string[],
  gameCounts: number[],
  accuracies: number[],
): ChartInstance {
  return new Chart(ctx, {
    type: 'bar',
    data: datasets(labels, gameCounts, accuracies),
    options: sharedChartOptions({
      ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
    }),
  });
}
