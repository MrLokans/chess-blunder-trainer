import type { ComponentChildren } from 'preact';
import { h } from 'preact';

export type CardElement = 'div' | 'section' | 'article';
export type CardBorder = 'top' | 'full';

export interface CardProps {
  as?: CardElement;
  border?: CardBorder;
  interactive?: boolean;
  selected?: boolean;
  onClick?: () => void;
  children?: ComponentChildren;
}

export function Card({
  as = 'div',
  border = 'full',
  interactive = false,
  selected = false,
  onClick,
  children,
}: CardProps) {
  const className = [
    'card-surface',
    border === 'top' ? 'card-surface--border-top' : '',
    interactive ? 'card-surface--interactive' : '',
    selected ? 'card-surface--selected' : '',
  ].filter(Boolean).join(' ');
  const props: Record<string, unknown> = { class: className };

  if (interactive) {
    props.onClick = onClick;
    props.tabIndex = 0;
    props.role = 'button';
    props.onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick?.();
      }
    };
  }

  return h(as, props, children);
}
