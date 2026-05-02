import type { ComponentChildren } from 'preact';

export type BadgeVariant = 'primary' | 'info' | 'warning' | 'danger' | 'neutral';

export interface BadgeProps {
  variant?: BadgeVariant;
  children?: ComponentChildren;
}

export function Badge({ variant = 'neutral', children }: BadgeProps) {
  return <span class={`badge badge--${variant}`}>{children}</span>;
}
