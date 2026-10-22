import type { ComponentChildren } from 'preact';

export type BadgeVariant = 'primary' | 'info' | 'warning' | 'danger' | 'neutral';

export interface BadgeProps {
  variant?: BadgeVariant;
  testId?: string;
  children?: ComponentChildren;
}

export function Badge({ variant = 'neutral', testId, children }: BadgeProps) {
  return <span class={`badge badge--${variant}`} data-testid={testId}>{children}</span>;
}
