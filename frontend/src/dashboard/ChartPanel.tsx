import { useRef, useEffect } from 'preact/hooks';

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

    chartRef.current = createChart(ctx, data.labels, data.gameCounts, data.accuracies);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [data, createChart]);

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
