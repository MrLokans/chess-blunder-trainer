import { useRef, useEffect, useState } from 'preact/hooks';

interface ChartPanelProps {
  title: string;
  description: string;
  emptyMessage: string;
  data: { labels: string[]; gameCounts: number[]; accuracies: number[] } | null;
  createChart: (ctx: CanvasRenderingContext2D, labels: string[], gameCounts: number[], accuracies: number[]) => ChartInstance;
}

export function ChartPanel({ title, description, emptyMessage, data, createChart }: ChartPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<ChartInstance | null>(null);
  const [themeVersion, setThemeVersion] = useState(0);

  useEffect(() => {
    const onThemeChange = () => { setThemeVersion(version => version + 1); };
    window.addEventListener('themechange', onThemeChange);
    return () => {
      window.removeEventListener('themechange', onThemeChange);
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

    // Canvas text is painted once, so wait for the web font or the axes keep the fallback face.
    let cancelled = false;
    const fontsReady = 'fonts' in document ? document.fonts.ready : Promise.resolve();
    void fontsReady.then(() => {
      if (!cancelled) chartRef.current = createChart(ctx, data.labels, data.gameCounts, data.accuracies);
    });

    return () => {
      cancelled = true;
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [data, createChart, themeVersion]);

  const isEmpty = !data || data.labels.length === 0;

  return (
    <div class="chart-container">
      <h3 class="chart-title">{title}</h3>
      <p class="chart-description">{description}</p>
      <div class={`chart-canvas-container ${isEmpty ? 'hidden' : ''}`}>
        <canvas ref={canvasRef} />
      </div>
      {isEmpty && <div class="chart-empty-state">{emptyMessage}</div>}
    </div>
  );
}
