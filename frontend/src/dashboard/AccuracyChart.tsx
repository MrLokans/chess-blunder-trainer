export interface AccuracySeries {
  labels: string[];
  gameCounts: number[];
  accuracies: number[];
}

interface AccuracyChartProps {
  title: string;
  description: string;
  emptyMessage: string;
  data: AccuracySeries | null;
}

export function accuracyRange(values: number[]): { low: number; step: number } {
  const low = Math.max(0, Math.floor((Math.min(...values) - 5) / 10) * 10);
  return { low, step: 100 - low > 40 ? 20 : 10 };
}

// A slot with no games has no accuracy; the line breaks there instead of diving to zero.
function segments(accuracies: (number | null)[]): Array<Array<[number, number]>> {
  const runs: Array<Array<[number, number]>> = [];
  let run: Array<[number, number]> = [];
  accuracies.forEach((value, i) => {
    if (value === null) {
      if (run.length > 0) runs.push(run);
      run = [];
    } else {
      run.push([i, value]);
    }
  });
  if (run.length > 0) runs.push(run);
  return runs;
}

function AccuracyPlot({ labels, gameCounts, accuracies }: AccuracySeries) {
  const values = accuracies.map((a, i) => ((gameCounts[i] ?? 0) > 0 ? a : null));
  const known = values.filter((v): v is number => v !== null);
  const { low, step } = accuracyRange(known);
  const y = (v: number) => (1 - (v - low) / (100 - low)) * 100;
  const ticks = Array.from({ length: Math.round((100 - low) / step) + 1 }, (_, i) => low + i * step);
  const maxGames = Math.max(...gameCounts, 1);
  const n = labels.length;
  const x = (i: number) => ((i + 0.5) / n) * 100;
  const labelEvery = Math.ceil(n / 8);

  return (
    <figure class="trend-chart accuracy-chart">
      <div class="trend-chart__plot accuracy-chart__plot" aria-hidden="true">
        {ticks.map(tick => (
          <span key={tick} class="trend-chart__tick" style={{ bottom: `${String(100 - y(tick))}%` }}>
            <span>{formatNumber(tick)}%</span>
          </span>
        ))}
        <svg class="accuracy-chart__line" viewBox="0 0 100 100" preserveAspectRatio="none">
          {segments(values).map(run => (
            <polyline
              key={run[0]?.[0]}
              points={run.map(([i, v]) => `${String(x(i))},${String(y(v))}`).join(' ')}
              vector-effect="non-scaling-stroke"
            />
          ))}
        </svg>
        {values.map((value, i) => value !== null && (
          <span
            key={labels[i]}
            class="accuracy-chart__dot"
            style={{ left: `${String(x(i))}%`, top: `${String(y(value))}%` }}
            title={`${labels[i] ?? ''}: ${formatNumber(value, { maximumFractionDigits: 1 })}% · ${t('dashboard.status.games', { count: gameCounts[i] ?? 0 })}`}
          />
        ))}
      </div>
      <div class="accuracy-chart__games" aria-hidden="true">
        {gameCounts.map((games, i) => (
          <span key={labels[i]} style={{ height: `${String((games / maxGames) * 100)}%` }} />
        ))}
      </div>
      <div class="trend-chart__axis" aria-hidden="true">
        {labels.map((label, i) => <span key={label}>{i % labelEvery === 0 ? label : ''}</span>)}
      </div>
      <figcaption class="trend-chart__note">
        <span class="accuracy-chart__key accuracy-chart__key--line">{t('dashboard.chart.accuracy')}</span>
        <span class="accuracy-chart__key accuracy-chart__key--games">{t('dashboard.chart.games_played')}</span>
      </figcaption>
      {/* Table elements ignore the 1px box, so the wrapper carries the hiding. */}
      <div class="sr-only">
        <table>
          <thead>
            <tr><th scope="col" /><th scope="col">{t('dashboard.chart.accuracy')}</th><th scope="col">{t('dashboard.chart.games_played')}</th></tr>
          </thead>
          <tbody>
            {labels.map((label, i) => {
              const value = values[i];
              return (
                <tr key={label}>
                  <th scope="row">{label}</th>
                  <td>{value === null || value === undefined ? '—' : `${formatNumber(value, { maximumFractionDigits: 1 })}%`}</td>
                  <td>{formatNumber(gameCounts[i] ?? 0)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

export function AccuracyChart({ title, description, emptyMessage, data }: AccuracyChartProps) {
  const hasData = data !== null && data.gameCounts.some(games => games > 0);
  return (
    <div class="chart-container">
      <h3 class="chart-title">{title}</h3>
      <p class="chart-description">{description}</p>
      {hasData ? <AccuracyPlot {...data} /> : <div class="chart-empty-state">{emptyMessage}</div>}
    </div>
  );
}
