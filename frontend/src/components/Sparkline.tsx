export interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  ariaLabel?: string;
}

const STROKE_PX = 1.5;

export function Sparkline({
  values,
  width = 120,
  height = 32,
  ariaLabel,
}: SparklineProps) {
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  // Avoid div-by-zero when the line is flat (`min === max`): plot at vertical midline.
  const span = max - min || 1;
  const xStep = (width - STROKE_PX) / (values.length - 1);

  const points = values.map((v, i) => {
    const x = STROKE_PX / 2 + i * xStep;
    const y = STROKE_PX / 2 + (height - STROKE_PX) * (1 - (v - min) / span);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const path = `M ${points.join(' L ')}`;

  const last = values[values.length - 1] ?? 0;
  const first = values[0] ?? 0;
  const trend = last >= first ? 'up' : 'down';

  return (
    <svg
      class={`sparkline sparkline--${trend}`}
      viewBox={`0 0 ${String(width)} ${String(height)}`}
      width={width}
      height={height}
      role="img"
      aria-label={ariaLabel}
      preserveAspectRatio="none"
    >
      <path d={path} fill="none" stroke="currentColor" stroke-width={STROKE_PX} />
    </svg>
  );
}
