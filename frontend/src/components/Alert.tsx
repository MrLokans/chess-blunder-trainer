export interface AlertProps {
  type: 'error' | 'success';
  message: string | null;
  // Opt-in override. Omitted, `role="alert"` already implies an assertive
  // live region; pass "polite" to soften it (e.g. form-level auth errors).
  live?: 'polite' | 'assertive';
}

export function Alert({ type, message, live }: AlertProps) {
  if (!message) return null;

  return (
    <div class={`alert alert-${type} visible`} role="alert" aria-live={live}>
      {message}
    </div>
  );
}
