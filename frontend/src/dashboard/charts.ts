function sharedChartOptions(xAxisConfig: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          label(context: { dataset: { yAxisID?: string; label?: string }; raw: number }) {
            if (context.dataset.yAxisID === 'y1') {
              return `${t('dashboard.chart.accuracy')}: ${context.raw.toFixed(1)}%`;
            }
            return `${context.dataset.label}: ${context.raw}`;
          },
        },
      },
    },
    scales: {
      x: xAxisConfig,
      y: {
        type: 'linear', display: true, position: 'left',
        title: { display: true, text: t('dashboard.chart.games_axis') },
        beginAtZero: true,
      },
      y1: {
        type: 'linear', display: true, position: 'right',
        title: { display: true, text: t('dashboard.chart.accuracy_axis') },
        min: 0, max: 100,
        grid: { drawOnChartArea: false },
      },
    },
  };
}

function datasets(labels: string[], gameCounts: number[], accuracies: number[]): ChartConfiguration['data'] {
  return {
    labels,
    datasets: [
      {
        label: t('dashboard.chart.games_played'),
        data: gameCounts,
        backgroundColor: 'rgba(26, 58, 143, 0.7)',
        borderColor: 'rgba(26, 58, 143, 1)',
        borderWidth: 1,
        yAxisID: 'y',
        order: 2,
      },
      {
        label: t('dashboard.chart.accuracy'),
        data: accuracies,
        type: 'line',
        borderColor: 'rgba(45, 143, 62, 1)',
        backgroundColor: 'rgba(45, 143, 62, 0.1)',
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
