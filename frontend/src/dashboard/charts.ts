interface ChartPalette {
  accent: string;
  success: string;
  text: string;
  muted: string;
  border: string;
  grid: string;
  surface: string;
}

function chartPalette(): ChartPalette {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string): string => style.getPropertyValue(name).trim() || fallback;
  return {
    accent: read('--accent', '#1A3A8F'), success: read('--success', '#2D8F3E'),
    text: read('--text', '#1A1A1A'), muted: read('--text-muted', '#706E68'),
    border: read('--border', '#B8B4AB'), grid: read('--border-subtle', '#E8E4DB'),
    surface: read('--surface-raised', '#F5F2EB'),
  };
}

function sharedChartOptions(xAxisConfig: Record<string, unknown> = {}): Record<string, unknown> {
  const colors = chartPalette();
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top', labels: { color: colors.text } },
      tooltip: {
        backgroundColor: colors.surface,
        titleColor: colors.text,
        bodyColor: colors.text,
        borderColor: colors.border,
        borderWidth: 1,
        callbacks: {
          label(context: { dataset: { yAxisID?: string; label?: string }; raw: number }) {
            if (context.dataset.yAxisID === 'y1') {
              return `${t('dashboard.chart.accuracy')}: ${context.raw.toFixed(1)}%`;
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
        ticks: { ...(xAxisConfig.ticks as Record<string, unknown>), color: colors.muted },
        grid: { ...(xAxisConfig.grid as Record<string, unknown>), color: colors.grid },
      },
      y: {
        type: 'linear', display: true, position: 'left',
        title: { display: true, text: t('dashboard.chart.games_axis'), color: colors.text },
        ticks: { color: colors.muted },
        grid: { color: colors.grid },
        beginAtZero: true,
      },
      y1: {
        type: 'linear', display: true, position: 'right',
        title: { display: true, text: t('dashboard.chart.accuracy_axis'), color: colors.text },
        ticks: { color: colors.muted },
        min: 0, max: 100,
        grid: { drawOnChartArea: false, color: colors.grid },
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
        backgroundColor: colors.accent,
        borderColor: colors.accent,
        borderWidth: 1,
        yAxisID: 'y',
        order: 2,
      },
      {
        label: t('dashboard.chart.accuracy'),
        data: accuracies,
        type: 'line',
        borderColor: colors.success,
        backgroundColor: colors.success,
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 3,
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
      ticks: { maxRotation: 45, minRotation: 45, maxTicksLimit: 15 },
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
      title: { display: true, text: t('dashboard.chart.hour_axis') },
    }),
  });
}
