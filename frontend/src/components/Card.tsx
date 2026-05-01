import type { ComponentChildren } from 'preact';
import { h } from 'preact';

export type CardElement = 'div' | 'section' | 'article';

export interface CardProps {
  as?: CardElement;
  interactive?: boolean;
  onClick?: () => void;
  children?: ComponentChildren;
}

export function Card({ as = 'div', interactive = false, onClick, children }: CardProps) {
  const className = `card-surface${interactive ? ' card-surface--interactive' : ''}`;
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
