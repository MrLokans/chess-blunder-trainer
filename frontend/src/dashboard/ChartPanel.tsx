import { useRef, useEffect, useState } from 'preact/hooks';

interface ChartPanelProps {
  title: string;
  description: string;
  emptyMessage: string;
  data: { labels: string[]; gameCounts: number[]; accuracies: number[] } | null;
  createChart: (ctx: CanvasRenderingContext2D, labels: string[], gameCounts: number[], accuracies: number[], timezone?: string) => ChartInstance;
  timezone?: string;
}

export function ChartPanel({ title, description, emptyMessage, data, createChart, timezone }: ChartPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartInstance | null>(null);
  const [themeVersion, setThemeVersion] = useState(0);

  useEffect(() => {
    const onThemeChange = () => { setThemeVersion(version => version + 1); };
    const onDisclosureOpen = () => { requestAnimationFrame(() => { chartRef.current?.resize(); }); };
    window.addEventListener('themechange', onThemeChange);
    window.addEventListener('dashboarddisclosureopen', onDisclosureOpen);
    return () => {
      window.removeEventListener('themechange', onThemeChange);
      window.removeEventListener('dashboarddisclosureopen', onDisclosureOpen);
    };
  }, []);

  useEffect(() => {
    if (!data || data.labels.length === 0) {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
      return;
    }

    if (chartRef.current) chartRef.current.destroy();

    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;

    chartRef.current = createChart(ctx, data.labels, data.gameCounts, data.accuracies, timezone);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [data, createChart, themeVersion, timezone]);

  const isEmpty = !data || data.labels.length === 0;

  return (
    <div class="chart-container">
      <div class="chart-title">{title}</div>
      <p class="chart-description">{description}</p>
      <div class={`chart-canvas-container ${isEmpty ? 'hidden' : ''}`}>
        <canvas ref={canvasRef} />
      </div>
      {isEmpty && <div class="chart-empty-state">{emptyMessage}</div>}
    </div>
  );
}
