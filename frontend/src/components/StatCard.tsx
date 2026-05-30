import type { ComponentChildren } from 'preact';

export interface StatCardDelta {
  value: string;
  direction: 'up' | 'down' | 'flat';
}

export interface StatCardProps {
  label: string;
  value: string | number;
  delta?: StatCardDelta;
  hint?: string;
  children?: ComponentChildren;
}

export function StatCard({ label, value, delta, hint, children }: StatCardProps) {
  return (
    <div class="stat-card">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{String(value)}</div>
      {delta && (
        <div class={`stat-delta stat-delta--${delta.direction}`}>{delta.value}</div>
      )}
      {hint && <div class="stat-hint">{hint}</div>}
      {children}
    </div>
  );
}
