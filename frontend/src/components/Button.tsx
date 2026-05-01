import type { ComponentChildren } from 'preact';
import { forwardRef } from 'preact/compat';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: () => void;
  ariaLabel?: string;
  children?: ComponentChildren;
}

export function buttonClassName(variant: ButtonVariant, size: ButtonSize, loading = false): string {
  return `btn btn--${variant} btn--${size}${loading ? ' btn--loading' : ''}`;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    type = 'button',
    onClick,
    ariaLabel,
    children,
  },
  ref,
) {
  const isDisabled = disabled || loading;

  return (
    <button
      ref={ref}
      type={type}
      class={buttonClassName(variant, size, loading)}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      aria-label={ariaLabel}
      onClick={onClick}
    >
      {loading && <span class="btn__spinner" aria-hidden="true" />}
      <span class="btn__label">{children}</span>
    </button>
  );
});
