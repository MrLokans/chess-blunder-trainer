import type { ComponentChildren } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { Alert } from '../../components/Alert';

export interface AuthCardProps {
  title: string;
  subtitle?: string;
  error: string | null;
  submitting: boolean;
  onSubmit: (e: Event) => void;
  footer?: ComponentChildren;
  children: ComponentChildren;
}

export function AuthCard({ title, subtitle, error, submitting, onSubmit, footer, children }: AuthCardProps) {
  const alertRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Pull keyboard focus to the error on failure. The Alert itself is an
    // aria-live region so screen readers announce the text; the focus move
    // brings sighted-keyboard users to it without re-announcing (the
    // wrapper has no accessible name of its own).
    if (error) alertRef.current?.focus();
  }, [error]);

  return (
    <div class="container">
      <div class="auth-card">
        <h1>{title}</h1>
        {subtitle && <p class="subtitle">{subtitle}</p>}
        <div ref={alertRef} tabIndex={-1} class="auth-alert-region">
          <Alert type="error" message={error} live="polite" />
        </div>
        <form class="auth-form" aria-busy={submitting || undefined} onSubmit={onSubmit}>
          {children}
        </form>
        {footer && <div class="auth-footer">{footer}</div>}
      </div>
    </div>
  );
}
