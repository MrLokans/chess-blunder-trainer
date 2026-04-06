export interface ProgressBarProps {
  current: number;
  total: number;
  textFormat?: (current: number, total: number) => string;
}

export function ProgressBar({ current, total, textFormat }: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  const text = textFormat
    ? textFormat(current, total)
    : `${String(current)}/${String(total)} (${String(percent)}%)`;

  return (
    <div class="progress-container">
      <div class="progress-fill" style={{ width: `${String(percent)}%` }} />
      <span class="progress-text">{text}</span>
    </div>
  );
}
