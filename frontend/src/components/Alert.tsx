export interface AlertProps {
  type: 'error' | 'success';
  message: string | null;
}

export function Alert({ type, message }: AlertProps) {
  if (!message) return null;

  return (
    <div class={`alert alert-${type} visible`} role="alert">
      {message}
    </div>
  );
}
